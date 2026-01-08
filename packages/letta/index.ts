/**
 * Deep Sci-Fi Letta Integration
 *
 * Main exports for the Letta agent orchestration system.
 */

// Orchestrator
export { LettaOrchestrator, getLettaOrchestrator } from './orchestrator';

// System Prompts
export { generateUserAgentSystemPrompt, generateWorldSystemPrompt } from './prompts';

// Tools
export {
  // User Agent Tools
  world_draft_generator,
  worldDraftGeneratorTool,
  list_worlds,
  listWorldsTool,
  user_preferences,
  userPreferencesTool,
  // World Agent Tools
  world_manager,
  worldManagerTool,
  story_manager,
  storyManagerTool,
  // Tool Arrays
  userAgentTools,
  worldAgentTools,
  // Tool Executor
  getUserAgentClientTools,
  getWorldAgentClientTools,
  executeTool,
  type ToolContext,
  type ClientTool,
} from './tools';

// Memory
export {
  getUserAgentMemoryBlocks,
  getWorldAgentMemoryBlocks,
  createMemoryBlocks,
  updateMemoryBlock,
  getAgentMemoryBlocks,
  cacheMemoryBlocks,
  getCachedMemoryBlocks,
} from './memory';

// Types
export type {
  AgentMessage,
  ChatSession,
  AgentResponse,
} from './types';
