/**
 * Tool Executor
 *
 * Executes client-side tools for Letta agents.
 * Handles tool calls, context passing, and error handling.
 */

import type Letta from '@letta-ai/letta-client';
import type { PrismaClient } from '@deep-sci-fi/db';
import { list_worlds, listWorldsTool } from './list-worlds';
import { user_preferences, userPreferencesTool } from './user-preferences';
import { world_manager, worldManagerTool } from './world-manager';
import { story_manager, storyManagerTool } from './story-manager';
import { image_generator, imageGeneratorTool } from './image-generator';
import { asset_manager, assetManagerTool } from './asset-manager';
import { canvas_ui, canvasUiTool } from './canvas-ui';
import { get_canvas_interactions, getCanvasInteractionsTool } from './get-canvas-interactions';
import { send_suggestion, sendSuggestionTool } from './send-suggestion';
import { delegate_to_experience } from './delegate-to-experience';

// Lazy import delegateToExperienceTool to avoid circular dependency
let _delegateToExperienceTool: any = null;
function getDelegateToExperienceTool() {
  if (!_delegateToExperienceTool) {
    _delegateToExperienceTool = require('./delegate-to-experience').delegateToExperienceTool;
  }
  return _delegateToExperienceTool;
}

/**
 * Tool execution context
 */
export interface ToolContext {
  userId: string;
  db: PrismaClient;
  worldId?: string;
  storyId?: string;
  worldName?: string;
  lettaClient?: Letta;
}

/**
 * Tool definition for Letta SDK
 */
export interface ClientTool {
  name: string;
  description: string;
  parameters: any;
}

/**
 * Tool executor function type
 */
type ToolExecutor = (params: any, context: ToolContext) => Promise<any>;

/**
 * Tool registry mapping tool names to executors
 */
const toolExecutors: Map<string, ToolExecutor> = new Map([
  ['list_worlds', list_worlds as ToolExecutor],
  ['user_preferences', user_preferences as ToolExecutor],
  ['world_manager', world_manager as ToolExecutor],
  ['story_manager', story_manager as ToolExecutor],
  ['image_generator', image_generator as ToolExecutor],
  ['asset_manager', asset_manager as ToolExecutor],
  ['canvas_ui', canvas_ui as unknown as ToolExecutor],
  ['get_canvas_interactions', get_canvas_interactions as unknown as ToolExecutor],
  ['send_suggestion', send_suggestion as unknown as ToolExecutor],
  ['delegate_to_experience', delegate_to_experience as unknown as ToolExecutor],
]);

/**
 * Get client tools for User Agent
 *
 * User Agent (Orchestrator) has tools for:
 * - Creating and managing worlds (via world_manager with create operation)
 * - Listing existing worlds
 * - Managing user preferences
 * - Delegating to Experience Agent for images and multimedia
 */
export function getUserAgentClientTools(): ClientTool[] {
  return [
    worldManagerTool,
    listWorldsTool,
    userPreferencesTool,
    getDelegateToExperienceTool(),
  ];
}

/**
 * Get client tools for World Agent
 */
export function getWorldAgentClientTools(): ClientTool[] {
  return [
    worldManagerTool,
    storyManagerTool,
    imageGeneratorTool,
    assetManagerTool,
    canvasUiTool,
    getCanvasInteractionsTool,
    sendSuggestionTool,
    getDelegateToExperienceTool(),
  ];
}

/**
 * Execute a tool by name
 *
 * @param toolName - Name of the tool to execute
 * @param params - Tool parameters
 * @param context - Execution context
 * @returns Tool execution result
 */
export async function executeTool(
  toolName: string,
  params: any,
  context: ToolContext
): Promise<any> {
  const executor = toolExecutors.get(toolName);

  if (!executor) {
    throw new Error(`Unknown tool: ${toolName}`);
  }

  try {
    console.log(`[ToolExecutor] Executing ${toolName} with params:`, params);
    const result = await executor(params, context);
    console.log(`[ToolExecutor] ${toolName} completed successfully`);
    return result;
  } catch (error) {
    console.error(`[ToolExecutor] ${toolName} failed:`, error);
    throw new Error(
      `Tool execution failed: ${toolName}\n${
        error instanceof Error ? error.message : String(error)
      }`
    );
  }
}

/**
 * Get all available tool names
 */
export function getAvailableToolNames(): string[] {
  return Array.from(toolExecutors.keys());
}
