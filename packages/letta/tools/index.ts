/**
 * Letta Agent Tools
 *
 * Tools are functions that agents can call to interact with the system.
 * They are registered with the Letta SDK when creating agents.
 */

// Import all tools first to ensure they're available for arrays
import {
  world_draft_generator,
  worldDraftGeneratorTool,
} from './world-draft-generator';

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
  world_draft_generator,
  worldDraftGeneratorTool,
  list_worlds,
  listWorldsTool,
  user_preferences,
  userPreferencesTool,
  world_manager,
  worldManagerTool,
  story_manager,
  storyManagerTool,
};

// World Agent Tools (remaining to be implemented)
// TODO: Implement these tools by porting from letta-code:
// - image_generator (generate images for scenes, characters, locations)
// - canvas_ui (create agent-driven UI components)
// - send_suggestion (proactive suggestions to user)

/**
 * All User Agent tool definitions for Letta SDK registration
 */
export const userAgentTools = [
  worldDraftGeneratorTool,
  listWorldsTool,
  userPreferencesTool,
];

/**
 * All World Agent tool definitions for Letta SDK registration
 */
export const worldAgentTools = [
  worldManagerTool,
  storyManagerTool,
  // TODO: Add remaining world agent tools:
  // - imageGeneratorTool
  // - canvasUiTool
  // - sendSuggestionTool
];
