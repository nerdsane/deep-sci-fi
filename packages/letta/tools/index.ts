/**
 * Letta Agent Tools
 *
 * Tools are functions that agents can call to interact with the system.
 * They are registered with the Letta SDK when creating agents.
 */

// Import all tools first to ensure they're available for arrays
import {
  list_worlds,
  listWorldsTool,
} from './list-worlds';

import {
  user_preferences,
  userPreferencesTool,
} from './user-preferences';

import {
  world_manager,
  worldManagerTool,
} from './world-manager';

import {
  story_manager,
  storyManagerTool,
} from './story-manager';

import {
  image_generator,
  imageGeneratorTool,
} from './image-generator';

import {
  asset_manager,
  assetManagerTool,
} from './asset-manager';

import {
  canvas_ui,
  canvasUiTool,
  broadcastStateChange,
} from './canvas-ui';

import {
  get_canvas_interactions,
  getCanvasInteractionsTool,
} from './get-canvas-interactions';

import {
  send_suggestion,
  sendSuggestionTool,
} from './send-suggestion';

import {
  delegate_to_experience,
  delegateToExperienceTool,
  getPendingDelegations,
  getDelegation,
  updateDelegation,
} from './delegate-to-experience';

// Tool Executor imports
export {
  getUserAgentClientTools,
  getWorldAgentClientTools,
  executeTool,
  type ToolContext,
  type ClientTool,
} from './executor';

// Export all tool functions and definitions
export {
  // User Agent Tools
  list_worlds,
  listWorldsTool,
  user_preferences,
  userPreferencesTool,
  // World Agent Tools
  world_manager,
  worldManagerTool,
  story_manager,
  storyManagerTool,
  image_generator,
  imageGeneratorTool,
  asset_manager,
  assetManagerTool,
  canvas_ui,
  canvasUiTool,
  broadcastStateChange,
  get_canvas_interactions,
  getCanvasInteractionsTool,
  send_suggestion,
  sendSuggestionTool,
  // Delegation
  delegate_to_experience,
  delegateToExperienceTool,
  getPendingDelegations,
  getDelegation,
  updateDelegation,
};

/**
 * All User Agent tool definitions for Letta SDK registration
 */
export const userAgentTools = [
  worldManagerTool,
  listWorldsTool,
  userPreferencesTool,
  delegateToExperienceTool,
];

/**
 * All World Agent tool definitions for Letta SDK registration
 */
export const worldAgentTools = [
  worldManagerTool,
  storyManagerTool,
  imageGeneratorTool,
  assetManagerTool,
  canvasUiTool,
  getCanvasInteractionsTool,
  sendSuggestionTool,
  delegateToExperienceTool,
];
