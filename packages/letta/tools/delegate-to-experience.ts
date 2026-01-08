/**
 * delegate_to_experience - World Agent tool for delegating to Experience Agent
 *
 * Allows the World Agent to delegate experience-crafting tasks to the
 * specialized Experience Agent for image generation, UI, and multimedia.
 */

import type Letta from '@letta-ai/letta-client';
import type { PrismaClient } from '@deep-sci-fi/db';
import {
  getOrCreateExperienceAgent,
  type ExperienceAgentConfig,
  type ExperienceAgentContext,
} from '../agents/experience-agent';

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
 * Extended context with Letta client for delegation
 */
export interface DelegationContext {
  userId: string;
  db: PrismaClient;
  worldId?: string;
  storyId?: string;
  lettaClient?: Letta;
  worldName?: string;
}

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
  context: DelegationContext
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

    if (!context.worldId) {
      return {
        success: false,
        message: 'Cannot delegate to Experience Agent: no world context available',
        delegation_id: '',
      };
    }

    if (!context.lettaClient) {
      return {
        success: false,
        message: 'Cannot delegate to Experience Agent: Letta client not available',
        delegation_id: '',
      };
    }

    // Create delegation record for tracking
    const delegationId = `del-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    const delegation: PendingDelegation = {
      id: delegationId,
      worldId: context.worldId,
      storyId: context.storyId,
      task: params.task,
      taskType: params.task_type,
      context: params.context || {},
      priority: params.priority || 'medium',
      status: 'in_progress',
      createdAt: new Date(),
    };

    delegationQueue.set(delegationId, delegation);

    console.log(
      `[delegate_to_experience] Starting delegation ${delegationId}: ${params.task_type}`
    );

    // Get world name for Experience Agent context
    let worldName = context.worldName || 'Unknown World';
    if (!context.worldName) {
      const world = await context.db.world.findUnique({
        where: { id: context.worldId },
        select: { name: true },
      });
      worldName = world?.name || worldName;
    }

    // Get or create Experience Agent for this world
    const experienceConfig: ExperienceAgentConfig = {
      lettaClient: context.lettaClient,
      db: context.db,
      userId: context.userId,
    };

    const experienceContext: ExperienceAgentContext = {
      worldId: context.worldId,
      worldName,
      storyId: context.storyId,
      storyTitle: undefined, // Could be populated if needed
    };

    const experienceAgentId = await getOrCreateExperienceAgent(
      experienceConfig,
      experienceContext
    );

    console.log(
      `[delegate_to_experience] Experience Agent created/found: ${experienceAgentId}`
    );

    // Build message for Experience Agent
    const taskMessage = buildTaskMessage(params);

    // Send task to Experience Agent and wait for response
    const response = await context.lettaClient.agents.messages.create(experienceAgentId, {
      messages: [{ role: 'user', content: taskMessage }],
      streaming: false,
    });

    console.log(`[delegate_to_experience] Experience Agent responded`);

    // Extract response content
    let responseText = '';
    if (response && 'messages' in response && Array.isArray(response.messages)) {
      for (const msg of response.messages) {
        if (msg && typeof msg === 'object' && 'message_type' in msg) {
          if (msg.message_type === 'assistant_message' && 'assistant_message' in msg) {
            responseText += msg.assistant_message + '\n';
          }
        }
      }
    }

    // Update delegation status
    delegation.status = 'completed';
    delegation.result = responseText;
    delegationQueue.set(delegationId, delegation);

    return {
      success: true,
      message: `Experience Agent completed "${params.task_type}" task.\n\nResult:\n${responseText.trim() || 'Task completed successfully.'}`,
      delegation_id: delegationId,
      experience_agent_id: experienceAgentId,
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

/**
 * Build a task message for the Experience Agent
 */
function buildTaskMessage(params: DelegateToExperienceParams): string {
  let message = `Task Type: ${params.task_type}\n\n`;
  message += `Task: ${params.task}\n`;

  if (params.context) {
    message += '\nContext:\n';
    if (params.context.scene_description) {
      message += `- Scene: ${params.context.scene_description}\n`;
    }
    if (params.context.character_names && params.context.character_names.length > 0) {
      message += `- Characters: ${params.context.character_names.join(', ')}\n`;
    }
    if (params.context.location) {
      message += `- Location: ${params.context.location}\n`;
    }
    if (params.context.mood) {
      message += `- Mood: ${params.context.mood}\n`;
    }
    if (params.context.style_hints) {
      message += `- Style: ${params.context.style_hints}\n`;
    }
    if (params.context.story_segment_id) {
      message += `- Story Segment ID: ${params.context.story_segment_id}\n`;
    }
  }

  if (params.priority) {
    message += `\nPriority: ${params.priority}\n`;
  }

  return message;
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
