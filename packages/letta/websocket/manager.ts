/**
 * WebSocket Manager
 *
 * Manages WebSocket connections between the Next.js server and browser clients.
 * Tools (canvas_ui, send_suggestion) use this to push updates to connected clients.
 * Browser interactions are queued here for agent polling.
 */

import type { ComponentSpec } from './types';

// ============================================================================
// Types
// ============================================================================

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

export interface InteractionMessage {
  type: 'interaction';
  componentId: string;
  interactionType: string;
  data: any;
  target?: string;
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

export interface ConnectionMessage {
  type: 'connect' | 'disconnect';
  clientType: 'canvas';
  clientId: string;
}

export interface ErrorMessage {
  type: 'error';
  error: string;
  details?: any;
}

export type WebSocketMessage =
  | CanvasUIMessage
  | StateChangeMessage
  | InteractionMessage
  | SuggestionMessage
  | ConnectionMessage
  | ErrorMessage;

export interface QueuedInteraction {
  id: string;
  timestamp: number;
  componentId: string;
  interactionType: string;
  target?: string;
  data: any;
}

// ============================================================================
// Interaction Queue
// ============================================================================

const interactionQueue: QueuedInteraction[] = [];
const MAX_QUEUE_SIZE = 100;
const INTERACTION_TTL_MS = 5 * 60 * 1000; // 5 minutes

/**
 * Queue an interaction from the browser
 */
export function queueInteraction(message: InteractionMessage): void {
  const queuedInteraction: QueuedInteraction = {
    id: `int-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    timestamp: Date.now(),
    componentId: message.componentId,
    interactionType: message.interactionType,
    target: message.target,
    data: message.data,
  };

  interactionQueue.push(queuedInteraction);

  // Trim queue if too large
  while (interactionQueue.length > MAX_QUEUE_SIZE) {
    interactionQueue.shift();
  }

  console.log(
    `[WebSocket Manager] Queued interaction: ${message.interactionType} on ${message.componentId} (queue size: ${interactionQueue.length})`
  );
}

/**
 * Get all pending interactions (clears queue)
 */
export function getInteractions(): QueuedInteraction[] {
  const now = Date.now();
  const validInteractions = interactionQueue.filter(
    (i) => now - i.timestamp < INTERACTION_TTL_MS
  );

  // Clear the queue
  interactionQueue.length = 0;

  return validInteractions;
}

/**
 * Peek at pending interactions without clearing
 */
export function peekInteractions(): QueuedInteraction[] {
  const now = Date.now();
  return interactionQueue.filter((i) => now - i.timestamp < INTERACTION_TTL_MS);
}

/**
 * Get count of pending interactions
 */
export function getInteractionCount(): number {
  const now = Date.now();
  return interactionQueue.filter((i) => now - i.timestamp < INTERACTION_TTL_MS)
    .length;
}

// ============================================================================
// Connected Clients Registry
// ============================================================================

/**
 * Polling-based message delivery system.
 *
 * How it works:
 * 1. Tools call broadcast() to queue messages
 * 2. Clients poll via /api/ws/poll endpoint (or SSE stream)
 * 3. getPendingMessages() returns and clears queued messages
 *
 * This is intentionally simple for the initial implementation.
 * For production, consider:
 * - Redis pub/sub for multi-instance support
 * - Server-Sent Events (SSE) for real-time without WebSocket complexity
 * - WebSocket via socket.io or ws for true bidirectional communication
 */

interface ConnectedClient {
  id: string;
  connectedAt: number;
  lastPollAt: number;
}

const connectedClients = new Map<string, ConnectedClient>();

// Messages pending delivery to clients via polling
const pendingMessages: WebSocketMessage[] = [];
const MAX_PENDING_MESSAGES = 1000;
const CLIENT_TIMEOUT_MS = 60000; // Consider client disconnected after 60s without polling

/**
 * Register a new client connection (or update last poll time)
 */
export function registerClient(clientId: string): void {
  const now = Date.now();
  const existing = connectedClients.get(clientId);

  connectedClients.set(clientId, {
    id: clientId,
    connectedAt: existing?.connectedAt || now,
    lastPollAt: now,
  });

  if (!existing) {
    console.log(
      `[WebSocket Manager] Client connected: ${clientId} (total: ${connectedClients.size})`
    );
  }
}

/**
 * Update client's last poll time (called on each poll)
 */
export function updateClientPoll(clientId: string): void {
  const existing = connectedClients.get(clientId);
  if (existing) {
    existing.lastPollAt = Date.now();
  } else {
    registerClient(clientId);
  }
}

/**
 * Clean up stale clients that haven't polled recently
 */
export function cleanupStaleClients(): number {
  const now = Date.now();
  let removed = 0;

  for (const [clientId, client] of connectedClients.entries()) {
    if (now - client.lastPollAt > CLIENT_TIMEOUT_MS) {
      connectedClients.delete(clientId);
      removed++;
    }
  }

  if (removed > 0) {
    console.log(
      `[WebSocket Manager] Cleaned up ${removed} stale clients (remaining: ${connectedClients.size})`
    );
  }

  return removed;
}

/**
 * Unregister a client connection
 */
export function unregisterClient(clientId: string): void {
  connectedClients.delete(clientId);
  console.log(
    `[WebSocket Manager] Client disconnected: ${clientId} (total: ${connectedClients.size})`
  );
}

/**
 * Get connected client count
 */
export function getClientCount(): number {
  return connectedClients.size;
}

// ============================================================================
// Message Broadcasting
// ============================================================================

/**
 * Broadcast a message to all connected clients.
 *
 * Messages are queued in memory and delivered when clients poll via getPendingMessages().
 * The browser client should poll regularly (e.g., every 500ms) to receive updates.
 */
export function broadcast(message: WebSocketMessage): void {
  pendingMessages.push(message);

  // Trim if too many pending
  while (pendingMessages.length > MAX_PENDING_MESSAGES) {
    pendingMessages.shift();
  }

  // Also cleanup stale clients periodically
  if (Math.random() < 0.1) {
    cleanupStaleClients();
  }

  console.log(
    `[WebSocket Manager] Queued ${message.type} message (pending: ${pendingMessages.length}, clients: ${connectedClients.size})`
  );
}

/**
 * Get pending messages for a client (clears queue after retrieval).
 *
 * Call this from a polling endpoint. The client should:
 * 1. Generate a unique clientId on first connect
 * 2. Poll this endpoint every 500ms (or use SSE stream)
 * 3. Process received messages to update UI
 *
 * @param clientId - Optional client ID to track polling activity
 */
export function getPendingMessages(clientId?: string): WebSocketMessage[] {
  // Track that client is still connected
  if (clientId) {
    updateClientPoll(clientId);
  }

  const messages = [...pendingMessages];
  pendingMessages.length = 0;
  return messages;
}

/**
 * Check if there are pending messages without clearing
 */
export function hasPendingMessages(): boolean {
  return pendingMessages.length > 0;
}

// ============================================================================
// Convenience Methods for Tools
// ============================================================================

/**
 * Send a canvas UI update
 */
export function sendCanvasUI(
  action: 'create' | 'update' | 'remove',
  target: string,
  componentId: string,
  spec?: ComponentSpec,
  mode: 'overlay' | 'fullscreen' | 'inline' = 'overlay'
): void {
  const message: CanvasUIMessage = {
    type: 'canvas_ui',
    action,
    target,
    componentId,
    spec,
    mode,
  };
  broadcast(message);
}

/**
 * Send a state change notification
 */
export function sendStateChange(
  event: StateChangeMessage['event'],
  data: Record<string, any>
): void {
  const message: StateChangeMessage = {
    type: 'state_change',
    event,
    data,
  };
  broadcast(message);
}

/**
 * Send a suggestion to the canvas
 */
export function sendSuggestion(
  title: string,
  description: string,
  priority: 'high' | 'medium' | 'low',
  actionId: string,
  actionLabel?: string,
  actionData?: any
): void {
  const message: SuggestionMessage = {
    type: 'suggestion',
    payload: {
      id: `sug-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      priority,
      title,
      description,
      actionId,
      actionLabel,
      actionData,
    },
  };
  broadcast(message);
}
