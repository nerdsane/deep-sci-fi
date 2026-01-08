import type { PrismaClient } from '@deep-sci-fi/db';

/**
 * List Worlds Tool
 *
 * Lists all worlds owned by the user
 * Used by User Agent (Orchestrator) when user wants to see their worlds
 */

/**
 * List the user's worlds
 *
 * @param params - Tool parameters (empty for now)
 * @param context - Tool execution context with database client
 * @returns Array of user's worlds with metadata
 */
export async function list_worlds(params: {}, context: {
  userId: string;
  db: PrismaClient;
}): Promise<Array<{
  id: string;
  name: string;
  visibility: string;
  storyCount: number;
  createdAt: Date;
  updatedAt: Date;
}>> {
  const { userId, db } = context;

  console.log(`[list_worlds] Fetching worlds for user: ${userId}`);

  // TODO: This will work once we pass the Prisma client in context
  try {
    const worlds = await db.world.findMany({
      where: { ownerId: userId },
      include: { _count: { select: { stories: true } } },
      orderBy: { updatedAt: 'desc' },
    });

    return worlds.map(world => ({
      id: world.id,
      name: world.name,
      visibility: world.visibility,
      storyCount: world._count.stories,
      createdAt: world.createdAt,
      updatedAt: world.updatedAt,
    }));
  } catch (error) {
    throw new Error(
      'list_worlds: Database query failed. ' +
      'Make sure Prisma client is passed in context. ' +
      `Error: ${error instanceof Error ? error.message : String(error)}`
    );
  }
}

/**
 * Tool definition for Letta agent registration
 */
export const listWorldsTool = {
  name: 'list_worlds',
  description: 'List all worlds owned by the user. Returns world names, visibility, story counts, and timestamps. Use this when the user asks to see their worlds or wants to select a world to work on.',
  parameters: {
    type: 'object',
    properties: {},
    required: [],
  },
};
