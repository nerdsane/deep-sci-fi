/**
 * Memory Block Manager
 *
 * Handles creation, updating, and caching of memory blocks for agents.
 */

import type Letta from '@letta-ai/letta-client';
import type { MemoryBlockDefinition } from './blocks';

export interface CreatedBlock {
  id: string;
  label: string;
}

/**
 * Create memory blocks for an agent
 *
 * @param client - Letta SDK client
 * @param blocks - Array of memory block definitions
 * @returns Array of created block IDs and labels
 */
export async function createMemoryBlocks(
  client: Letta,
  blocks: MemoryBlockDefinition[]
): Promise<CreatedBlock[]> {
  const createdBlocks: CreatedBlock[] = [];

  for (const block of blocks) {
    try {
      const createdBlock = await client.blocks.create({
        label: block.label,
        value: block.value,
        description: block.description,
        limit: block.limit,
        ...(block.read_only !== undefined && { read_only: block.read_only }),
      });

      if (!createdBlock.id) {
        throw new Error(`Created block ${block.label} has no ID`);
      }

      createdBlocks.push({
        id: createdBlock.id,
        label: block.label,
      });

      console.log(`Created memory block: ${block.label} (${createdBlock.id})`);
    } catch (error) {
      console.error(`Failed to create memory block ${block.label}:`, error);
      throw new Error(
        `Failed to create memory block ${block.label}: ${
          error instanceof Error ? error.message : String(error)
        }`
      );
    }
  }

  return createdBlocks;
}

/**
 * Update a memory block's value
 *
 * @param client - Letta SDK client
 * @param agentId - Agent ID that owns the block
 * @param blockLabel - Label of the block to update
 * @param value - New value for the block
 */
export async function updateMemoryBlock(
  client: Letta,
  agentId: string,
  blockLabel: string,
  value: string
): Promise<void> {
  try {
    await client.agents.blocks.update(blockLabel, {
      agent_id: agentId,
      value,
    });

    console.log(`Updated memory block: ${blockLabel} for agent ${agentId}`);
  } catch (error) {
    console.error(`Failed to update memory block ${blockLabel}:`, error);
    throw new Error(
      `Failed to update memory block ${blockLabel}: ${
        error instanceof Error ? error.message : String(error)
      }`
    );
  }
}

/**
 * Get memory blocks for an agent
 *
 * @param client - Letta SDK client
 * @param agentId - Agent ID
 * @returns Array of memory blocks
 */
export async function getAgentMemoryBlocks(
  client: Letta,
  agentId: string
): Promise<any[]> {
  try {
    // Retrieve agent with memory blocks included
    const agent = await client.agents.retrieve(agentId, {
      include: ['agent.memory_blocks'],
    });

    return agent.memory?.blocks || [];
  } catch (error) {
    console.error(`Failed to get memory blocks for agent ${agentId}:`, error);
    throw new Error(
      `Failed to get memory blocks: ${
        error instanceof Error ? error.message : String(error)
      }`
    );
  }
}

/**
 * Cache memory blocks in database (for faster access)
 *
 * @param db - Prisma client
 * @param agentId - Letta agent ID
 * @param userId - User ID (for user agents)
 * @param worldId - World ID (for world agents)
 * @param memoryBlocks - Memory blocks to cache
 */
export async function cacheMemoryBlocks(
  db: any, // PrismaClient type
  agentId: string,
  userId: string | null,
  worldId: string | null,
  memoryBlocks: CreatedBlock[]
): Promise<void> {
  try {
    await db.agentSession.upsert({
      where: { agentId },
      create: {
        agentId,
        userId,
        worldId,
        memoryBlocks: memoryBlocks,
        lastActiveAt: new Date(),
      },
      update: {
        memoryBlocks: memoryBlocks,
        lastActiveAt: new Date(),
      },
    });

    console.log(`Cached memory blocks for agent ${agentId}`);
  } catch (error) {
    console.error(`Failed to cache memory blocks for agent ${agentId}:`, error);
    // Don't throw - caching is optional
  }
}

/**
 * Get cached memory blocks from database
 *
 * @param db - Prisma client
 * @param agentId - Letta agent ID
 * @returns Cached memory blocks or null
 */
export async function getCachedMemoryBlocks(
  db: any, // PrismaClient type
  agentId: string
): Promise<CreatedBlock[] | null> {
  try {
    const session = await db.agentSession.findUnique({
      where: { agentId },
      select: { memoryBlocks: true },
    });

    return session?.memoryBlocks as CreatedBlock[] || null;
  } catch (error) {
    console.error(`Failed to get cached memory blocks for agent ${agentId}:`, error);
    return null;
  }
}
