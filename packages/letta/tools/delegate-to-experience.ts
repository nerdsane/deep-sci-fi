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
  getExperienceAgentTools,
  type ExperienceAgentConfig,
  type ExperienceAgentContext,
} from '../agents/experience-agent';
import { executeTool, type ToolContext } from './executor';

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
  world_id?: string; // Optional - can be passed explicitly if not in context (e.g., from User Agent)
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

    // Use world_id from params if not in context (e.g., User Agent after creating a world)
    const worldId = context.worldId || params.world_id;

    if (!worldId) {
      return {
        success: false,
        message: 'Cannot delegate to Experience Agent: no world context available. Either provide world_id parameter or enter a world first.',
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
      worldId: worldId,
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
        where: { id: worldId },
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
      worldId: worldId,
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

    // Get client tools for Experience Agent
    const clientTools = getExperienceAgentTools();

    // Validate that tools loaded correctly
    if (!clientTools || clientTools.length === 0) {
      console.error('[delegate_to_experience] Experience Agent tools failed to load!');
      delegation.status = 'failed';
      delegationQueue.set(delegationId, delegation);
      return {
        success: false,
        message: 'Experience Agent tools failed to load. This is an internal error.',
        delegation_id: delegationId,
      };
    }

    console.log(`[delegate_to_experience] Loaded ${clientTools.length} client tools: ${clientTools.map(t => t.name).join(', ')}`);

    // Tool execution context for Experience Agent tools
    const toolContext: ToolContext = {
      userId: context.userId,
      db: context.db,
      worldId: worldId,
      storyId: context.storyId,
      worldName,
      lettaClient: context.lettaClient,
    };

    // Send task to Experience Agent with approval handling loop
    let responseText = '';
    let currentInput: any = [{ role: 'user', content: taskMessage }];
    let loopCount = 0;
    const maxLoops = 10;
    const toolFailures: Array<{ toolName: string; error: string }> = [];

    while (loopCount < maxLoops) {
      loopCount++;
      const approvalRequests = new Map<string, { toolName: string; args: string }>();
      let stopReason: string | undefined;

      console.log(`[delegate_to_experience] Sending message to Experience Agent (loop ${loopCount})`);

      // Stream from Experience Agent to capture all message types
      const stream = await context.lettaClient.agents.messages.create(experienceAgentId, {
        messages: currentInput,
        streaming: true,
        stream_tokens: true,
        client_tools: clientTools,
      });

      // Process stream chunks
      for await (const chunk of stream) {
        if (!chunk || typeof chunk !== 'object') continue;

        const chunkAny = chunk as any;
        const messageType = chunkAny.message_type;

        switch (messageType) {
          case 'stop_reason':
            stopReason = chunkAny.stop_reason;
            break;

          case 'assistant_message': {
            let content = '';
            if (typeof chunkAny.content === 'string') {
              content = chunkAny.content;
            } else if (Array.isArray(chunkAny.content)) {
              for (const part of chunkAny.content) {
                if (part?.type === 'text' && part.text) {
                  content += part.text;
                }
              }
            }
            if (content) {
              responseText += content;
            }
            break;
          }

          case 'approval_request_message': {
            const toolCall = chunkAny.tool_call ||
              (Array.isArray(chunkAny.tool_calls) && chunkAny.tool_calls[0]);
            if (toolCall?.tool_call_id && toolCall?.name) {
              const existing = approvalRequests.get(toolCall.tool_call_id);
              approvalRequests.set(toolCall.tool_call_id, {
                toolName: toolCall.name,
                args: (existing?.args || '') + (toolCall.arguments || ''),
              });
              console.log(`[delegate_to_experience] Tool needs approval: ${toolCall.name}`);
            }
            break;
          }

          case 'tool_call_message': {
            const toolCall = chunkAny.tool_call ||
              (Array.isArray(chunkAny.tool_calls) && chunkAny.tool_calls[0]);
            if (toolCall) {
              console.log(`[delegate_to_experience] Tool call: ${toolCall.name}`);
            }
            break;
          }
        }
      }

      console.log(`[delegate_to_experience] Stream complete. Stop reason: ${stopReason}, Approvals: ${approvalRequests.size}`);

      // End of turn - break
      if (stopReason === 'end_turn') {
        break;
      }

      // Requires approval - execute tools and continue
      if (stopReason === 'requires_approval' && approvalRequests.size > 0) {
        const approvalResults = [];

        for (const [toolCallId, { toolName, args }] of approvalRequests.entries()) {
          console.log(`[delegate_to_experience] Executing tool: ${toolName}`);

          try {
            const parsedArgs = args ? JSON.parse(args) : {};
            const result = await executeTool(toolName, parsedArgs, toolContext);

            console.log(`[delegate_to_experience] Tool ${toolName} completed successfully`);
            approvalResults.push({
              type: 'tool',
              tool_call_id: toolCallId,
              tool_return: JSON.stringify(result),
              status: 'success',
            });
          } catch (error) {
            const errorMsg = error instanceof Error ? error.message : String(error);
            console.error(`[delegate_to_experience] Tool ${toolName} failed:`, error);
            toolFailures.push({ toolName, error: errorMsg });
            approvalResults.push({
              type: 'tool',
              tool_call_id: toolCallId,
              tool_return: `Error: ${errorMsg}`,
              status: 'error',
            });
          }
        }

        // Send approval results back and continue loop
        currentInput = [{ type: 'approval', approvals: approvalResults }] as any;
        continue;
      }

      // Unknown stop reason - break
      break;
    }

    console.log(`[delegate_to_experience] Experience Agent completed after ${loopCount} loops`);

    // Check for tool failures
    if (toolFailures.length > 0) {
      console.error('[delegate_to_experience] Tool failures occurred:', toolFailures);
      delegation.status = 'failed';
      delegation.result = {
        responseText,
        errors: toolFailures,
      };
      delegationQueue.set(delegationId, delegation);

      const errorDetails = toolFailures.map(f => `- ${f.toolName}: ${f.error}`).join('\n');
      return {
        success: false,
        message: `Experience Agent task "${params.task_type}" had tool failures:\n${errorDetails}\n\nPartial response:\n${responseText.trim() || 'No response'}`,
        delegation_id: delegationId,
        experience_agent_id: experienceAgentId,
      };
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
      world_id: {
        type: 'string',
        description: 'World ID to delegate for. Required if not already in a world context (e.g., when using from User Agent after creating a world)',
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
