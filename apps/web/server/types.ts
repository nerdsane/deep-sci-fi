/**
 * Unified WebSocket Protocol Types
 *
 * This defines the message protocol for bidirectional communication
 * between Browser (Chat + Canvas), CLI, and the Agent.
 */

import type { ComponentSpec } from '@deep-sci-fi/letta/websocket/types';

// ============================================================================
// Client Types
// ============================================================================

export type ClientType = 'browser' | 'cli';

export interface Client {
  id: string;
  type: ClientType;
  ws: WebSocket;
  connectedAt: number;
  sessionId: string;
}

export interface Session {
  id: string;
  userId: string;
  clients: Map<string, Client>;
  worldContext?: {
    worldId?: string;
    storyId?: string;
    worldName?: string;
  };
  createdAt: number;
}

// ============================================================================
// Client → Server Messages
// ============================================================================

export interface ChatMessage {
  type: 'chat_message';
  content: string;
  context?: {
    worldId?: string;
    storyId?: string;
  };
}

export interface InteractionMessage {
  type: 'interaction';
  componentId: string;
  interactionType: string;
  data: any;
  target?: string;
}

export interface PingMessage {
  type: 'ping';
}

export type ClientToServerMessage = ChatMessage | InteractionMessage | PingMessage;

// ============================================================================
// Server → Client Messages
// ============================================================================

export interface ConnectMessage {
  type: 'connect';
  clientId: string;
  sessionId: string;
  connectedClients: Array<{ id: string; type: ClientType }>;
}

export interface ClientJoinedMessage {
  type: 'client_joined';
  client: {
    id: string;
    type: ClientType;
  };
}

export interface ClientLeftMessage {
  type: 'client_left';
  clientId: string;
  clientType: ClientType;
}

export interface ChatChunkMessage {
  type: 'chat_chunk';
  chunk: {
    type: 'reasoning' | 'reasoning_end' | 'tool_call' | 'tool_result' | 'assistant' | 'assistant_end' | 'error' | 'warning' | 'info' | 'done' | 'usage';
    id?: string;
    content?: string;
    toolCallId?: string;
    toolName?: string;
    toolArgs?: string;
    toolResult?: string;
    toolStatus?: 'pending' | 'running' | 'success' | 'error';
    usage?: {
      promptTokens?: number;
      completionTokens?: number;
      totalTokens?: number;
    };
    stopReason?: string;
  };
}

export interface CanvasUIMessage {
  type: 'canvas_ui';
  action: 'create' | 'update' | 'remove';
  target: string;
  componentId: string;
  spec?: ComponentSpec;
  mode?: 'overlay' | 'fullscreen' | 'inline';
}

export interface StateChangeMessage {
  type: 'state_change';
  event:
    | 'story_started'
    | 'story_continued'
    | 'branch_selected'
    | 'world_entered'
    | 'image_generated'
    | 'agent_thinking'
    | 'agent_done';
  data: Record<string, any>;
}

export interface SuggestionMessage {
  type: 'suggestion';
  payload: {
    id: string;
    priority: 'high' | 'medium' | 'low';
    title: string;
    description: string;
    actionId: string;
    actionLabel?: string;
    actionData?: any;
  };
}

export interface ErrorMessage {
  type: 'error';
  error: string;
  details?: any;
}

export interface PongMessage {
  type: 'pong';
}

export interface MessageHistoryMessage {
  type: 'message_history';
  messages: Array<{
    id: string;
    role: string;
    content: string;
    messageType: string;
    toolName?: string | null;
    toolArgs?: string | null;
    toolResult?: string | null;
    toolStatus?: string | null;
    createdAt: string;
  }>;
}

export type ServerToClientMessage =
  | ConnectMessage
  | ClientJoinedMessage
  | ClientLeftMessage
  | ChatChunkMessage
  | CanvasUIMessage
  | StateChangeMessage
  | SuggestionMessage
  | ErrorMessage
  | PongMessage
  | MessageHistoryMessage;

// ============================================================================
// Combined Message Type
// ============================================================================

export type WebSocketMessage = ClientToServerMessage | ServerToClientMessage;

// ============================================================================
// Interaction Queue (for agent polling)
// ============================================================================

export interface QueuedInteraction {
  id: string;
  timestamp: number;
  sessionId: string;
  componentId: string;
  interactionType: string;
  target?: string;
  data: any;
}
