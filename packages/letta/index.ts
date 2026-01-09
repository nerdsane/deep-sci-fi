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

// Agents
export {
  generateExperienceAgentSystemPrompt,
  getExperienceAgentMemoryBlocks,
  getExperienceAgentTools,
  getOrCreateExperienceAgent,
  type ExperienceAgentContext,
  type ExperienceAgentConfig,
} from './agents';

// WebSocket Manager (for Canvas UI communication)
export {
  queueInteraction,
  getInteractions,
  peekInteractions,
  getInteractionCount,
  broadcast,
  getPendingMessages,
  hasPendingMessages,
  registerClient,
  updateClientPoll,
  cleanupStaleClients,
  getClientCount,
  sendCanvasUI,
  sendStateChange,
  sendSuggestion as sendSuggestionToCanvas,
  setActiveBroadcastHandler,
  getActiveBroadcastHandler,
  type QueuedInteraction,
  type WebSocketMessage,
  type ComponentSpec,
} from './websocket';

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
  StreamChunk,
  StreamChunkType,
} from './types';
