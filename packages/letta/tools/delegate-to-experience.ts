/**
 * delegate_to_experience - World Agent tool for delegating to Experience Agent
 *
 * Allows the World Agent to delegate experience-crafting tasks to the
 * specialized Experience Agent for image generation, UI, and multimedia.
 */

import type { PrismaClient } from '@deep-sci-fi/db';

// ============================================================================
// Types
// ============================================================================

export interface DelegateToExperienceParams {
  task: string;
  task_type:
    | 'generate_image'
    | 'create_ui'
    | 'manage_assets'
    | 'enhance_scene'
    | 'create_gallery'
    | 'other';
  context?: {
    scene_description?: string;
    character_names?: string[];
    location?: string;
    mood?: string;
    style_hints?: string;
    story_segment_id?: string;
  };
  priority?: 'high' | 'medium' | 'low';
}

export interface DelegateToExperienceResult {
  success: boolean;
  message: string;
  delegation_id: string;
  experience_agent_id?: string;
}

// ============================================================================
// Delegation Queue (in-memory for now, can move to Redis/DB)
// ============================================================================

export interface PendingDelegation {
  id: string;
  worldId: string;
  storyId?: string;
  task: string;
  taskType: string;
  context: Record<string, any>;
  priority: 'high' | 'medium' | 'low';
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  createdAt: Date;
  result?: any;
}

const delegationQueue: Map<string, PendingDelegation> = new Map();

/**
 * Get pending delegations for a world
 */
export function getPendingDelegations(worldId: string): PendingDelegation[] {
  return Array.from(delegationQueue.values())
    .filter((d) => d.worldId === worldId && d.status === 'pending')
    .sort((a, b) => {
      const priorityOrder = { high: 0, medium: 1, low: 2 };
      return priorityOrder[a.priority] - priorityOrder[b.priority];
    });
}

/**
 * Get a specific delegation
 */
export function getDelegation(id: string): PendingDelegation | undefined {
  return delegationQueue.get(id);
}

/**
 * Update delegation status
 */
export function updateDelegation(
  id: string,
  updates: Partial<PendingDelegation>
): void {
  const delegation = delegationQueue.get(id);
  if (delegation) {
    Object.assign(delegation, updates);
    delegationQueue.set(id, delegation);
  }
}

// ============================================================================
// Main Entry Point
// ============================================================================

/**
 * Delegate a task to the Experience Agent.
 *
 * Use this when you need:
 * - Images generated for scenes, characters, or locations
 * - Dynamic UI components created in the canvas
 * - Asset management and organization
 * - Visual enhancements for story moments
 */
export async function delegate_to_experience(
  params: DelegateToExperienceParams,
  context: { userId: string; db: PrismaClient; worldId: string; storyId?: string }
): Promise<DelegateToExperienceResult> {
  try {
    if (!params.task) {
      return {
        success: false,
        message: 'task is required - describe what you want the Experience Agent to do',
        delegation_id: '',
      };
    }

    if (!params.task_type) {
      return {
        success: false,
        message:
          'task_type is required (generate_image, create_ui, manage_assets, enhance_scene, create_gallery, other)',
        delegation_id: '',
      };
    }

    // Create delegation record
    const delegationId = `del-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    const delegation: PendingDelegation = {
      id: delegationId,
      worldId: context.worldId,
      storyId: context.storyId,
      task: params.task,
      taskType: params.task_type,
      context: params.context || {},
      priority: params.priority || 'medium',
      status: 'pending',
      createdAt: new Date(),
    };

    delegationQueue.set(delegationId, delegation);

    console.log(
      `[delegate_to_experience] Created delegation ${delegationId}: ${params.task_type}`
    );

    // In a full implementation, this would:
    // 1. Look up or create the Experience Agent for this world
    // 2. Send the task to the Experience Agent
    // 3. Wait for or stream the response back
    // For now, we queue the delegation for the orchestrator to handle

    return {
      success: true,
      message: `Delegated "${params.task_type}" task to Experience Agent.\nDelegation ID: ${delegationId}\nThe Experience Agent will handle: ${params.task}`,
      delegation_id: delegationId,
    };
  } catch (error) {
    console.error('[delegate_to_experience] Error:', error);
    return {
      success: false,
      message: `Failed to delegate: ${error instanceof Error ? error.message : String(error)}`,
      delegation_id: '',
    };
  }
}

// ============================================================================
// Tool Definition for Letta SDK
// ============================================================================

export const delegateToExperienceTool = {
  name: 'delegate_to_experience',
  description:
    'Delegate a task to the Experience Agent for image generation, UI creation, and visual enhancements. Use when you need images, visual components, or multimedia assets.',
  parameters: {
    type: 'object',
    properties: {
      task: {
        type: 'string',
        description:
          'Description of what you want the Experience Agent to create or do',
      },
      task_type: {
        type: 'string',
        enum: [
          'generate_image',
          'create_ui',
          'manage_assets',
          'enhance_scene',
          'create_gallery',
          'other',
        ],
        description: 'Type of task being delegated',
      },
      context: {
        type: 'object',
        description: 'Additional context for the task',
        properties: {
          scene_description: {
            type: 'string',
            description: 'Description of the scene for visual generation',
          },
          character_names: {
            type: 'array',
            items: { type: 'string' },
            description: 'Characters involved in the scene',
          },
          location: {
            type: 'string',
            description: 'Location where the scene takes place',
          },
          mood: {
            type: 'string',
            description: 'Emotional tone or mood to convey',
          },
          style_hints: {
            type: 'string',
            description: 'Art style or visual hints',
          },
          story_segment_id: {
            type: 'string',
            description: 'Story segment this relates to',
          },
        },
      },
      priority: {
        type: 'string',
        enum: ['high', 'medium', 'low'],
        description: 'Task priority (default: medium)',
      },
    },
    required: ['task', 'task_type'],
  },
};
