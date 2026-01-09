/**
 * world_manager - Database-based world management tool for Deep Sci-Fi web
 *
 * Operations:
 * - save: Persist world to database
 * - load: Restore world from database
 * - diff: Compare two world versions (future feature)
 * - update: Evolve the world incrementally
 *
 * This is adapted from letta-code's filesystem-based world_manager
 * to work with the Prisma database.
 */

import type { PrismaClient } from '@deep-sci-fi/db';

// ============================================================================
// Tool Interface
// ============================================================================

export interface WorldManagerParams {
  operation: 'create' | 'save' | 'load' | 'update';
  world_id?: string; // Database world ID (cuid) - required for save/load/update, not for create
  name?: string; // For create operation
  description?: string; // For create operation
  world_data?: any; // For save/create operation - full world foundation data
  updates?: Array<{
    path: string; // Dot-notation path (e.g., "rules.0.statement")
    operation: 'add' | 'update' | 'remove';
    value?: any;
    reason?: string; // Human-readable reason for this update
  }>; // For update operation
}

export interface WorldManagerResult {
  success: boolean;
  message: string;
  world?: {
    id: string;
    name: string;
    description: string | null;
    foundation: any;
    version: number;
    updatedAt: Date;
  };
}

// ============================================================================
// Main Entry Point
// ============================================================================

export async function world_manager(
  params: WorldManagerParams,
  context: { userId: string; db: PrismaClient }
): Promise<WorldManagerResult> {
  try {
    console.log(`[world_manager] Operation: ${params.operation}${params.world_id ? ` for world ${params.world_id}` : ''}`);

    // Validate operation
    if (!['create', 'save', 'load', 'update'].includes(params.operation)) {
      return {
        success: false,
        message: `Invalid operation: ${params.operation}. Valid operations: create, save, load, update`,
      };
    }

    // Handle create operation separately (doesn't need existing world)
    if (params.operation === 'create') {
      return await createWorld(params, context);
    }

    // For other operations, world_id is required
    if (!params.world_id) {
      return {
        success: false,
        message: `world_id is required for ${params.operation} operation`,
      };
    }

    // Verify world exists and user owns it
    const world = await context.db.world.findUnique({
      where: { id: params.world_id },
      select: {
        id: true,
        name: true,
        description: true,
        foundation: true,
        ownerId: true,
        updatedAt: true,
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
      case 'save':
        return await saveWorld(params, context.db, world);
      case 'load':
        return await loadWorld(world);
      case 'update':
        return await updateWorld(params, context.db, world);
      default:
        return {
          success: false,
          message: `Unknown operation: ${params.operation}`,
        };
    }
  } catch (error) {
    console.error('[world_manager] Error:', error);
    return {
      success: false,
      message: `Error in world_manager: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

// ============================================================================
// Operation: Create
// ============================================================================

async function createWorld(
  params: WorldManagerParams,
  context: { userId: string; db: PrismaClient }
): Promise<WorldManagerResult> {
  // Validate required fields for create
  if (!params.name?.trim()) {
    return {
      success: false,
      message: 'name is required for create operation',
    };
  }

  if (!params.world_data) {
    return {
      success: false,
      message: 'world_data is required for create operation (foundation data for the world)',
    };
  }

  try {
    // Ensure world_data has required foundation fields
    const foundation = params.world_data;
    if (!foundation.premise) {
      return {
        success: false,
        message: 'world_data.premise is required',
      };
    }

    // Create world in database
    const world = await context.db.world.create({
      data: {
        name: params.name.trim(),
        description: params.description || `A sci-fi world: ${foundation.premise.substring(0, 100)}...`,
        foundation: foundation,
        ownerId: context.userId,
      },
      select: {
        id: true,
        name: true,
        description: true,
        foundation: true,
        updatedAt: true,
      },
    });

    console.log(`[world_manager] World created: ${world.id} (${world.name})`);

    return {
      success: true,
      message: `World "${world.name}" created successfully!\nWorld ID: ${world.id}\nYou can now enter this world to develop it further.`,
      world: {
        id: world.id,
        name: world.name,
        description: world.description,
        foundation: world.foundation,
        version: 1,
        updatedAt: world.updatedAt,
      },
    };
  } catch (error) {
    console.error('[world_manager] Create failed:', error);
    return {
      success: false,
      message: `Failed to create world: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

// ============================================================================
// Operation: Save
// ============================================================================

async function saveWorld(
  params: WorldManagerParams,
  db: PrismaClient,
  currentWorld: any
): Promise<WorldManagerResult> {
  if (!params.world_data) {
    return {
      success: false,
      message: 'world_data is required for save operation',
    };
  }

  try {
    // Update world in database
    const updatedWorld = await db.world.update({
      where: { id: params.world_id },
      data: {
        foundation: params.world_data,
        updatedAt: new Date(),
      },
      select: {
        id: true,
        name: true,
        description: true,
        foundation: true,
        updatedAt: true,
      },
    });

    console.log(`[world_manager] World saved: ${updatedWorld.id}`);

    return {
      success: true,
      message: `World saved successfully\nWorld: ${updatedWorld.name}\nUpdated: ${updatedWorld.updatedAt.toISOString()}`,
      world: {
        ...updatedWorld,
        version: 1, // Version tracking not yet in database schema
      },
    };
  } catch (error) {
    console.error('[world_manager] Save failed:', error);
    return {
      success: false,
      message: `Failed to save world: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

// ============================================================================
// Operation: Load
// ============================================================================

async function loadWorld(world: any): Promise<WorldManagerResult> {
  console.log(`[world_manager] World loaded: ${world.id}`);

  return {
    success: true,
    message: `World loaded successfully\nWorld: ${world.name}\nDescription: ${world.description || 'No description'}`,
    world: {
      id: world.id,
      name: world.name,
      description: world.description,
      foundation: world.foundation,
      version: 1, // Version tracking not yet in database schema
      updatedAt: world.updatedAt,
    },
  };
}

// ============================================================================
// Operation: Update
// ============================================================================

async function updateWorld(
  params: WorldManagerParams,
  db: PrismaClient,
  currentWorld: any
): Promise<WorldManagerResult> {
  if (!params.updates || params.updates.length === 0) {
    return {
      success: false,
      message: 'updates array is required for update operation',
    };
  }

  try {
    // Get current foundation data
    let foundation = currentWorld.foundation || {};

    // Apply each update
    const revisionNotes: string[] = [];

    for (let i = 0; i < params.updates.length; i++) {
      const update = params.updates[i];

      if (!update) {
        continue;
      }

      // Validate update
      if (!update.path) {
        return {
          success: false,
          message: `Update at index ${i} is missing required 'path' field`,
        };
      }

      if (!update.operation || !['add', 'update', 'remove'].includes(update.operation)) {
        return {
          success: false,
          message: `Update at index ${i} has invalid 'operation' field`,
        };
      }

      // Apply update
      foundation = applyUpdate(foundation, update);

      if (update.reason) {
        revisionNotes.push(update.reason);
      }
    }

    // Save updated foundation to database
    const updatedWorld = await db.world.update({
      where: { id: params.world_id },
      data: {
        foundation,
        updatedAt: new Date(),
      },
      select: {
        id: true,
        name: true,
        description: true,
        foundation: true,
        updatedAt: true,
      },
    });

    console.log(`[world_manager] World updated: ${updatedWorld.id} (${revisionNotes.length} changes)`);

    const message = `World updated successfully\nChanges applied: ${params.updates.length}\n` +
      (revisionNotes.length > 0 ? `Revision notes:\n${revisionNotes.map(note => `  - ${note}`).join('\n')}` : '');

    return {
      success: true,
      message,
      world: {
        id: updatedWorld.id,
        name: updatedWorld.name,
        description: updatedWorld.description,
        foundation: updatedWorld.foundation,
        version: 1, // Version tracking not yet in database schema
        updatedAt: updatedWorld.updatedAt,
      },
    };
  } catch (error) {
    console.error('[world_manager] Update failed:', error);
    return {
      success: false,
      message: `Failed to update world: ${error instanceof Error ? error.message : String(error)}`,
    };
  }
}

/**
 * Apply a single update operation to the foundation data
 */
function applyUpdate(foundation: any, update: { path: string; operation: string; value?: any }): any {
  const path = update.path.split('.');
  const newFoundation = JSON.parse(JSON.stringify(foundation)); // Deep clone

  let current: any = newFoundation;

  // Navigate to the parent of the target field
  for (let i = 0; i < path.length - 1; i++) {
    const key = path[i];
    if (!key) continue;

    // Create intermediate objects if they don't exist
    if (!current[key]) {
      current[key] = {};
    }

    current = current[key];
  }

  const lastKey = path[path.length - 1];
  if (!lastKey) {
    throw new Error('Invalid path: empty key');
  }

  // Apply the operation
  switch (update.operation) {
    case 'add':
      if (Array.isArray(current[lastKey])) {
        current[lastKey].push(update.value);
      } else {
        current[lastKey] = update.value;
      }
      break;

    case 'update':
      current[lastKey] = update.value;
      break;

    case 'remove':
      if (Array.isArray(current[lastKey])) {
        // Assume value is the ID or index to remove
        if (typeof update.value === 'number') {
          current[lastKey].splice(update.value, 1);
        } else {
          current[lastKey] = current[lastKey].filter((item: any) =>
            item.id !== update.value
          );
        }
      } else {
        delete current[lastKey];
      }
      break;
  }

  return newFoundation;
}

// ============================================================================
// Tool Definition for Letta SDK
// ============================================================================

export const worldManagerTool = {
  name: 'world_manager',
  description: 'Manage world data in the database. Operations: create (new world from draft), save (persist world), load (retrieve world), update (incremental changes with path-based operations)',
  parameters: {
    type: 'object',
    properties: {
      operation: {
        type: 'string',
        enum: ['create', 'save', 'load', 'update'],
        description: 'Operation to perform: create (new world), save, load, or update',
      },
      world_id: {
        type: 'string',
        description: 'Database ID of the world (cuid) - required for save/load/update, not needed for create',
      },
      name: {
        type: 'string',
        description: 'Name of the world (required for create operation)',
      },
      description: {
        type: 'string',
        description: 'Brief description of the world (optional for create, auto-generated if not provided)',
      },
      world_data: {
        type: 'object',
        description: 'Full world foundation data (required for create and save operations). Should include: premise, technology, society, and optionally physics and history',
        properties: {
          premise: {
            type: 'string',
            description: 'The core concept or "what if" that defines this world',
          },
          technology: {
            type: 'string',
            description: 'The level and nature of technology in this world',
          },
          society: {
            type: 'string',
            description: 'Social structures, governance, culture',
          },
          physics: {
            type: 'string',
            description: 'Any unique physical laws or phenomena (optional)',
          },
          history: {
            type: 'string',
            description: 'Key historical events that shaped this world (optional)',
          },
        },
      },
      updates: {
        type: 'array',
        description: 'Array of update operations (for update operation)',
        items: {
          type: 'object',
          properties: {
            path: {
              type: 'string',
              description: 'Dot-notation path to the field (e.g., "rules.0.statement")',
            },
            operation: {
              type: 'string',
              enum: ['add', 'update', 'remove'],
              description: 'Operation: add (append to array or set field), update (replace field), remove (delete field or array item)',
            },
            value: {
              description: 'Value for the operation (not needed for remove)',
            },
            reason: {
              type: 'string',
              description: 'Human-readable reason for this update',
            },
          },
          required: ['path', 'operation'],
        },
      },
    },
    required: ['operation'],
  },
};
