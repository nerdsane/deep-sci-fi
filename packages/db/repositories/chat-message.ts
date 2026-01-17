import type { PrismaClient, ChatMessage } from '@prisma/client';

export interface SaveMessageData {
  userId: string;
  worldId?: string | null;
  storyId?: string | null;
  role: string;
  content: string;
  messageType: string;
  toolName?: string | null;
  toolArgs?: string | null;
  toolResult?: string | null;
  toolStatus?: string | null;
}

export interface GetMessagesParams {
  userId: string;
  worldId?: string | null; // null = User Agent messages (no world context)
  limit?: number;
  before?: Date;
}

/**
 * Save a chat message to the database
 */
export async function saveMessage(
  db: PrismaClient,
  data: SaveMessageData
): Promise<ChatMessage> {
  return db.chatMessage.create({
    data: {
      userId: data.userId,
      worldId: data.worldId ?? null,
      storyId: data.storyId ?? null,
      role: data.role,
      content: data.content,
      messageType: data.messageType,
      toolName: data.toolName ?? null,
      toolArgs: data.toolArgs ?? null,
      toolResult: data.toolResult ?? null,
      toolStatus: data.toolStatus ?? null,
    },
  });
}

/**
 * Get chat messages for a user, optionally filtered by world context
 *
 * When worldId is null: Returns messages where worldId IS NULL (User Agent context)
 * When worldId is undefined: Returns all messages regardless of world
 * When worldId is a string: Returns messages for that specific world
 */
export async function getMessages(
  db: PrismaClient,
  params: GetMessagesParams
): Promise<ChatMessage[]> {
  const { userId, worldId, limit = 50, before } = params;

  const where: {
    userId: string;
    worldId?: string | null;
    createdAt?: { lt: Date };
  } = { userId };

  // Handle worldId filtering
  if (worldId === null) {
    // Explicitly want User Agent messages (no world)
    where.worldId = null;
  } else if (worldId !== undefined) {
    // Want messages for a specific world
    where.worldId = worldId;
  }
  // If worldId is undefined, don't filter by world at all

  if (before) {
    where.createdAt = { lt: before };
  }

  // Get the most recent messages by ordering desc and taking limit
  // Then reverse to display in chronological order (oldest to newest within the selected set)
  const messages = await db.chatMessage.findMany({
    where,
    orderBy: { createdAt: 'desc' },
    take: limit,
  });

  // Reverse to display in chronological order (oldest first within the recent batch)
  return messages.reverse();
}

/**
 * Delete all messages for a user (optional: in a specific world context)
 */
export async function deleteMessages(
  db: PrismaClient,
  params: { userId: string; worldId?: string | null }
): Promise<number> {
  const { userId, worldId } = params;

  const where: { userId: string; worldId?: string | null } = { userId };

  if (worldId === null) {
    where.worldId = null;
  } else if (worldId !== undefined) {
    where.worldId = worldId;
  }

  const result = await db.chatMessage.deleteMany({ where });
  return result.count;
}
