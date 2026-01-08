/**
 * story_manager - Database-based story management tool for Deep Sci-Fi web
 *
 * Operations:
 * - create: Create a new story in a world
 * - save_segment: Add a story segment
 * - load: Load story with all segments
 * - list: List stories for a world
 *
 * This is adapted from letta-code's filesystem-based story_manager
 * to work with the Prisma database.
 */

import type { PrismaClient } from '@deep-sci-fi/db';

// ============================================================================
// Tool Interface
// ============================================================================

export interface StoryManagerParams {
  operation: 'create' | 'save_segment' | 'load' | 'list';
  world_id: string; // Database world ID (cuid)
  story_id?: string; // Database story ID (cuid) - required for save_segment, load
  title?: string; // Required for create
  description?: string; // Optional for create
  segment?: {
    title?: string;
    content: string;
    metadata?: any;
  }; // Required for save_segment
}

export interface StoryManagerResult {
  success: boolean;
  message: string;
  story?: any;
  segment?: any;
  stories?: any[];
}

// ============================================================================
// Main Entry Point
// ============================================================================

export async function story_manager(
  params: StoryManagerParams,
  context: { userId: string; db: PrismaClient }
): Promise<StoryManagerResult> {
  try {
    console.log(`[story_manager] Operation: ${params.operation} for world ${params.world_id}`);

    // Validate operation
    if (!['create', 'save_segment', 'load', 'list'].includes(params.operation)) {
      return {
        success: false,
        message: `Invalid operation: ${params.operation}. Valid operations: create, save_segment, load, list`,
      };
    }

    // Verify world exists and user owns it
    const world = await context.db.world.findUnique({
      where: { id: params.world_id },
      select: {
        id: true,
        name: true,
        ownerId: true,
      },
    });

    if (!world) {
      return {
        success: false,
        message: `World not found: ${params.world_id}`,
      };
    }

    if (world.ownerId !== context.userId) {
      return {
        success: false,
        message: `Permission denied: You don't own world ${params.world_id}`,
      };
    }

    // Route to operation handler
    switch (params.operation) {
      case 'create':
        return await createStory(params, context.db, world);
      case 'save_segment':
        return await saveSegment(params, context.db, world);
      case 'load':
        return await loadStory(params, context.db);
      case 'list':
        return await listStories(params, context.db);
      default:
        return {
          success: false,
          message: `Unknown operation: ${params.operation}`,
        };
    }
  } catch (error) {
    console.error('[story_manager] Error:', error);
    return {
      success: false,
      message: `Error in story_manager: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

// ============================================================================
// Operation: Create Story
// ============================================================================

async function createStory(
  params: StoryManagerParams,
  db: PrismaClient,
  world: any
): Promise<StoryManagerResult> {
  if (!params.title) {
    return {
      success: false,
      message: 'title is required for create operation',
    };
  }

  try {
    // Create story in database
    const story = await db.story.create({
      data: {
        title: params.title,
        description: params.description || null,
        worldId: params.world_id,
        metadata: {}, // Empty metadata initially
      },
      select: {
        id: true,
        title: true,
        description: true,
        worldId: true,
        createdAt: true,
        updatedAt: true,
      },
    });

    console.log(`[story_manager] Story created: ${story.id} in world ${world.name}`);

    return {
      success: true,
      message: `Story created: ${story.title}\nID: ${story.id}\nWorld: ${world.name}\nCreated: ${story.createdAt.toISOString()}`,
      story,
    };
  } catch (error) {
    console.error('[story_manager] Create failed:', error);
    return {
      success: false,
      message: `Failed to create story: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

// ============================================================================
// Operation: Save Segment
// ============================================================================

async function saveSegment(
  params: StoryManagerParams,
  db: PrismaClient,
  world: any
): Promise<StoryManagerResult> {
  if (!params.story_id) {
    return {
      success: false,
      message: 'story_id is required for save_segment operation',
    };
  }

  if (!params.segment) {
    return {
      success: false,
      message: 'segment is required for save_segment operation',
    };
  }

  try {
    // Verify story exists and belongs to the world
    const story = await db.story.findUnique({
      where: { id: params.story_id },
      select: {
        id: true,
        title: true,
        worldId: true,
        _count: {
          select: { segments: true },
        },
      },
    });

    if (!story) {
      return {
        success: false,
        message: `Story not found: ${params.story_id}`,
      };
    }

    if (story.worldId !== params.world_id) {
      return {
        success: false,
        message: `Story ${params.story_id} does not belong to world ${params.world_id}`,
      };
    }

    // Create segment
    const segment = await db.storySegment.create({
      data: {
        storyId: params.story_id,
        title: params.segment.title || null,
        content: params.segment.content,
        order: story._count.segments + 1, // Next order number
        metadata: params.segment.metadata || {},
      },
      select: {
        id: true,
        title: true,
        content: true,
        order: true,
        createdAt: true,
      },
    });

    // Update story's updatedAt timestamp
    await db.story.update({
      where: { id: params.story_id },
      data: { updatedAt: new Date() },
    });

    console.log(`[story_manager] Segment saved: ${segment.id} to story ${story.title}`);

    const contentPreview = segment.content.substring(0, 100) + (segment.content.length > 100 ? '...' : '');

    return {
      success: true,
      message: `Segment saved to story "${story.title}"\nSegment ID: ${segment.id}\nOrder: ${segment.order}\nPreview: ${contentPreview}`,
      segment,
    };
  } catch (error) {
    console.error('[story_manager] Save segment failed:', error);
    return {
      success: false,
      message: `Failed to save segment: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

// ============================================================================
// Operation: Load Story
// ============================================================================

async function loadStory(
  params: StoryManagerParams,
  db: PrismaClient
): Promise<StoryManagerResult> {
  if (!params.story_id) {
    return {
      success: false,
      message: 'story_id is required for load operation',
    };
  }

  try {
    const story = await db.story.findUnique({
      where: { id: params.story_id },
      include: {
        segments: {
          orderBy: { order: 'asc' },
          select: {
            id: true,
            title: true,
            content: true,
            order: true,
            metadata: true,
            createdAt: true,
          },
        },
        world: {
          select: {
            id: true,
            name: true,
          },
        },
      },
    });

    if (!story) {
      return {
        success: false,
        message: `Story not found: ${params.story_id}`,
      };
    }

    console.log(`[story_manager] Story loaded: ${story.title} (${story.segments.length} segments)`);

    return {
      success: true,
      message: `Story loaded: "${story.title}"\nWorld: ${story.world.name}\nSegments: ${story.segments.length}\nCreated: ${story.createdAt.toISOString()}`,
      story,
    };
  } catch (error) {
    console.error('[story_manager] Load failed:', error);
    return {
      success: false,
      message: `Failed to load story: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

// ============================================================================
// Operation: List Stories
// ============================================================================

async function listStories(
  params: StoryManagerParams,
  db: PrismaClient
): Promise<StoryManagerResult> {
  try {
    const stories = await db.story.findMany({
      where: { worldId: params.world_id },
      include: {
        _count: {
          select: { segments: true },
        },
      },
      orderBy: { createdAt: 'desc' },
      select: {
        id: true,
        title: true,
        description: true,
        createdAt: true,
        updatedAt: true,
        _count: true,
      },
    });

    console.log(`[story_manager] Listed ${stories.length} stories for world ${params.world_id}`);

    const summary = stories.length > 0
      ? stories.map(s =>
          `- ${s.title} (${s.id})\n  Segments: ${s._count.segments}, Created: ${s.createdAt.toISOString()}`
        ).join('\n')
      : 'No stories yet';

    return {
      success: true,
      message: `Found ${stories.length} stories in world:\n${summary}`,
      stories,
    };
  } catch (error) {
    console.error('[story_manager] List failed:', error);
    return {
      success: false,
      message: `Failed to list stories: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

// ============================================================================
// Tool Definition for Letta SDK
// ============================================================================

export const storyManagerTool = {
  name: 'story_manager',
  description: 'Manage stories and story segments in the database. Operations: create (new story), save_segment (add segment to story), load (retrieve story with segments), list (get all stories in world)',
  parameters: {
    type: 'object',
    properties: {
      operation: {
        type: 'string',
        enum: ['create', 'save_segment', 'load', 'list'],
        description: 'Operation to perform: create, save_segment, load, or list',
      },
      world_id: {
        type: 'string',
        description: 'Database ID of the world (cuid)',
      },
      story_id: {
        type: 'string',
        description: 'Database ID of the story (cuid) - required for save_segment and load',
      },
      title: {
        type: 'string',
        description: 'Story title (required for create operation)',
      },
      description: {
        type: 'string',
        description: 'Story description (optional for create operation)',
      },
      segment: {
        type: 'object',
        description: 'Segment data (required for save_segment operation)',
        properties: {
          title: {
            type: 'string',
            description: 'Segment title (optional)',
          },
          content: {
            type: 'string',
            description: 'Segment content (required)',
          },
          metadata: {
            type: 'object',
            description: 'Additional metadata for the segment',
          },
        },
        required: ['content'],
      },
    },
    required: ['operation', 'world_id'],
  },
};
