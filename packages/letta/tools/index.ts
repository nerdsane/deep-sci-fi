/**
 * Letta Agent Tools
 *
 * Tools are functions that agents can call to interact with the system.
 * They are registered with the Letta SDK when creating agents.
 */

// User Agent Tools (Orchestrator)
export {
  world_draft_generator,
  worldDraftGeneratorTool,
} from './world-draft-generator';

export {
  list_worlds,
  listWorldsTool,
} from './list-worlds';

export {
  user_preferences,
  userPreferencesTool,
} from './user-preferences';

// World Agent Tools (to be implemented)
// TODO: Implement these tools by porting from letta-code:
// - world_manager (save/load/diff/update world data)
// - story_manager (create/save stories and segments)
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
  // TODO: Add world agent tools when implemented
  // worldManagerTool,
  // storyManagerTool,
  // imageGeneratorTool,
  // canvasUiTool,
  // sendSuggestionTool,
];
