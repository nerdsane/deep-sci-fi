/**
 * WebSocket Message Types
 *
 * Defines all message types for communication between:
 * - Next.js Server (tool executor) → Browser (Canvas UI)
 * - Browser (user interactions) → Next.js Server
 */

import type { ComponentSpec } from '@/components/canvas/types';

// ============================================================================
// Server → Client Messages
// ============================================================================

/**
 * Canvas UI update message
 * Sent when an agent calls the canvas_ui tool
 */
export interface CanvasUpdateMessage {
  type: 'canvas_update';
  action: 'create' | 'update' | 'remove';
  target: string; // Mount point: 'story_segment_123', 'world_overview', 'floating'
  componentId: string;
  spec?: ComponentSpec; // Omit for 'remove'
  mode?: 'overlay' | 'fullscreen' | 'inline';
}

/**
 * State change notification
 * Sent when significant state changes occur during agent execution
 */
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
  data: {
    storyId?: string;
    worldId?: string;
    segmentId?: string;
    branchId?: string;
    assetPath?: string;
    [key: string]: unknown;
  };
}

/**
 * Suggestion message
 * Sent when agent wants to proactively suggest an action
 */
export interface SuggestionMessage {
  type: 'suggestion';
  payload: {
    id: string;
    priority: 'high' | 'medium' | 'low';
    title: string;
    description: string;
    actionId: string;
    actionLabel?: string;
    actionData?: unknown;
  };
}

/**
 * Connection acknowledgment
 * Sent after client successfully connects
 */
export interface ConnectionAckMessage {
  type: 'connection_ack';
  clientId: string;
  serverTime: number;
}

/**
 * Error message
 * Sent when an error occurs
 */
export interface ErrorMessage {
  type: 'error';
  error: string;
  code?: string;
  details?: unknown;
}

/**
 * Ping/Pong for keepalive
 */
export interface PingMessage {
  type: 'ping';
  timestamp: number;
}

export interface PongMessage {
  type: 'pong';
  timestamp: number;
}

// ============================================================================
// Client → Server Messages
// ============================================================================

/**
 * User interaction event
 * Sent when user interacts with a Canvas UI component
 */
export interface InteractionMessage {
  type: 'interaction';
  componentId: string;
  interactionType: string; // 'click', 'input_change', 'dialog_close', etc.
  data: unknown;
  target?: string; // Optional callback handler name from spec
}

/**
 * Client identification
 * Sent when client first connects
 */
export interface ClientIdentifyMessage {
  type: 'identify';
  clientType: 'canvas' | 'debug';
  userId?: string;
  sessionId?: string;
}

/**
 * Subscribe to specific events
 */
export interface SubscribeMessage {
  type: 'subscribe';
  topics: string[]; // e.g., ['world:abc123', 'story:def456']
}

/**
 * Unsubscribe from events
 */
export interface UnsubscribeMessage {
  type: 'unsubscribe';
  topics: string[];
}

// ============================================================================
// Union Types
// ============================================================================

/**
 * All server-to-client messages
 */
export type ServerMessage =
  | CanvasUpdateMessage
  | StateChangeMessage
  | SuggestionMessage
  | ConnectionAckMessage
  | ErrorMessage
  | PongMessage;

/**
 * All client-to-server messages
 */
export type ClientMessage =
  | InteractionMessage
  | ClientIdentifyMessage
  | SubscribeMessage
  | UnsubscribeMessage
  | PingMessage;

/**
 * All WebSocket messages
 */
export type WebSocketMessage = ServerMessage | ClientMessage;

// ============================================================================
// Helper Types
// ============================================================================

/**
 * Client connection info stored in manager
 */
export interface ClientInfo {
  id: string;
  clientType: 'canvas' | 'debug';
  userId?: string;
  sessionId?: string;
  subscriptions: Set<string>;
  connectedAt: number;
  lastActivity: number;
}

/**
 * Interaction stored in queue for agent consumption
 */
export interface QueuedInteraction {
  id: string;
  clientId: string;
  componentId: string;
  interactionType: string;
  data: unknown;
  target?: string;
  timestamp: number;
}
