/**
 * WebSocket Connection Manager
 *
 * Manages WebSocket connections, message routing, and interaction queues.
 * This is a singleton that runs on the server side.
 */

import type { WebSocket } from 'ws';
import { nanoid } from 'nanoid';
import type {
  ClientInfo,
  ClientMessage,
  ServerMessage,
  QueuedInteraction,
  CanvasUpdateMessage,
  StateChangeMessage,
  SuggestionMessage,
} from './types';

/**
 * WebSocket Connection Manager
 *
 * Responsibilities:
 * - Track all connected clients
 * - Route messages to appropriate clients (by userId, topic subscription)
 * - Queue interactions for agent consumption
 * - Handle client lifecycle (connect, identify, disconnect)
 */
class WebSocketManager {
  private clients: Map<string, { ws: WebSocket; info: ClientInfo }> = new Map();
  private userToClients: Map<string, Set<string>> = new Map();
  private topicToClients: Map<string, Set<string>> = new Map();
  private interactionQueue: Map<string, QueuedInteraction[]> = new Map(); // userId -> interactions

  /**
   * Register a new WebSocket connection
   */
  addClient(ws: WebSocket): string {
    const clientId = nanoid();
    const info: ClientInfo = {
      id: clientId,
      clientType: 'canvas',
      subscriptions: new Set(),
      connectedAt: Date.now(),
      lastActivity: Date.now(),
    };

    this.clients.set(clientId, { ws, info });

    console.log(`[WebSocketManager] Client connected: ${clientId}`);

    return clientId;
  }

  /**
   * Handle client identification (after connect)
   */
  identifyClient(
    clientId: string,
    clientType: 'canvas' | 'debug',
    userId?: string,
    sessionId?: string
  ): void {
    const client = this.clients.get(clientId);
    if (!client) {
      console.warn(`[WebSocketManager] Cannot identify unknown client: ${clientId}`);
      return;
    }

    client.info.clientType = clientType;
    client.info.userId = userId;
    client.info.sessionId = sessionId;
    client.info.lastActivity = Date.now();

    // Track user -> clients mapping
    if (userId) {
      let userClients = this.userToClients.get(userId);
      if (!userClients) {
        userClients = new Set();
        this.userToClients.set(userId, userClients);
      }
      userClients.add(clientId);
    }

    console.log(
      `[WebSocketManager] Client identified: ${clientId} as ${clientType}` +
        (userId ? ` for user ${userId}` : '')
    );
  }

  /**
   * Remove a client connection
   */
  removeClient(clientId: string): void {
    const client = this.clients.get(clientId);
    if (!client) {
      return;
    }

    // Remove from user mapping
    if (client.info.userId) {
      const userClients = this.userToClients.get(client.info.userId);
      if (userClients) {
        userClients.delete(clientId);
        if (userClients.size === 0) {
          this.userToClients.delete(client.info.userId);
        }
      }
    }

    // Remove from topic subscriptions
    for (const topic of client.info.subscriptions) {
      const topicClients = this.topicToClients.get(topic);
      if (topicClients) {
        topicClients.delete(clientId);
        if (topicClients.size === 0) {
          this.topicToClients.delete(topic);
        }
      }
    }

    this.clients.delete(clientId);
    console.log(`[WebSocketManager] Client disconnected: ${clientId}`);
  }

  /**
   * Subscribe client to topics
   */
  subscribe(clientId: string, topics: string[]): void {
    const client = this.clients.get(clientId);
    if (!client) {
      return;
    }

    for (const topic of topics) {
      client.info.subscriptions.add(topic);

      let topicClients = this.topicToClients.get(topic);
      if (!topicClients) {
        topicClients = new Set();
        this.topicToClients.set(topic, topicClients);
      }
      topicClients.add(clientId);
    }

    client.info.lastActivity = Date.now();
    console.log(`[WebSocketManager] Client ${clientId} subscribed to: ${topics.join(', ')}`);
  }

  /**
   * Unsubscribe client from topics
   */
  unsubscribe(clientId: string, topics: string[]): void {
    const client = this.clients.get(clientId);
    if (!client) {
      return;
    }

    for (const topic of topics) {
      client.info.subscriptions.delete(topic);

      const topicClients = this.topicToClients.get(topic);
      if (topicClients) {
        topicClients.delete(clientId);
        if (topicClients.size === 0) {
          this.topicToClients.delete(topic);
        }
      }
    }

    client.info.lastActivity = Date.now();
  }

  /**
   * Send message to a specific client
   */
  sendToClient(clientId: string, message: ServerMessage): boolean {
    const client = this.clients.get(clientId);
    if (!client || client.ws.readyState !== 1 /* WebSocket.OPEN */) {
      return false;
    }

    try {
      client.ws.send(JSON.stringify(message));
      return true;
    } catch (error) {
      console.error(`[WebSocketManager] Failed to send to client ${clientId}:`, error);
      return false;
    }
  }

  /**
   * Send message to all clients of a user
   */
  sendToUser(userId: string, message: ServerMessage): number {
    const clientIds = this.userToClients.get(userId);
    if (!clientIds) {
      return 0;
    }

    let sent = 0;
    for (const clientId of clientIds) {
      if (this.sendToClient(clientId, message)) {
        sent++;
      }
    }

    return sent;
  }

  /**
   * Send message to all clients subscribed to a topic
   */
  sendToTopic(topic: string, message: ServerMessage): number {
    const clientIds = this.topicToClients.get(topic);
    if (!clientIds) {
      return 0;
    }

    let sent = 0;
    for (const clientId of clientIds) {
      if (this.sendToClient(clientId, message)) {
        sent++;
      }
    }

    return sent;
  }

  /**
   * Broadcast message to all connected clients
   */
  broadcast(message: ServerMessage): number {
    let sent = 0;
    for (const clientId of this.clients.keys()) {
      if (this.sendToClient(clientId, message)) {
        sent++;
      }
    }
    return sent;
  }

  // ============================================================================
  // Canvas UI Methods (called by tool executor)
  // ============================================================================

  /**
   * Send canvas UI update (from canvas_ui tool)
   */
  sendCanvasUpdate(
    userId: string,
    update: Omit<CanvasUpdateMessage, 'type'>
  ): number {
    const message: CanvasUpdateMessage = {
      type: 'canvas_update',
      ...update,
    };

    console.log(
      `[WebSocketManager] Canvas update: ${update.action} ${update.componentId} for user ${userId}`
    );

    return this.sendToUser(userId, message);
  }

  /**
   * Send state change notification
   */
  sendStateChange(
    userId: string,
    event: StateChangeMessage['event'],
    data: StateChangeMessage['data']
  ): number {
    const message: StateChangeMessage = {
      type: 'state_change',
      event,
      data,
    };

    console.log(`[WebSocketManager] State change: ${event} for user ${userId}`);

    return this.sendToUser(userId, message);
  }

  /**
   * Send suggestion to user
   */
  sendSuggestion(
    userId: string,
    suggestion: SuggestionMessage['payload']
  ): number {
    const message: SuggestionMessage = {
      type: 'suggestion',
      payload: suggestion,
    };

    console.log(`[WebSocketManager] Suggestion: ${suggestion.title} for user ${userId}`);

    return this.sendToUser(userId, message);
  }

  // ============================================================================
  // Interaction Queue (for get_canvas_interactions tool)
  // ============================================================================

  /**
   * Queue an interaction from a client
   */
  queueInteraction(
    clientId: string,
    componentId: string,
    interactionType: string,
    data: unknown,
    target?: string
  ): void {
    const client = this.clients.get(clientId);
    if (!client || !client.info.userId) {
      console.warn(
        `[WebSocketManager] Cannot queue interaction: client ${clientId} not identified`
      );
      return;
    }

    const userId = client.info.userId;
    const interaction: QueuedInteraction = {
      id: nanoid(),
      clientId,
      componentId,
      interactionType,
      data,
      target,
      timestamp: Date.now(),
    };

    let queue = this.interactionQueue.get(userId);
    if (!queue) {
      queue = [];
      this.interactionQueue.set(userId, queue);
    }
    queue.push(interaction);

    client.info.lastActivity = Date.now();

    console.log(
      `[WebSocketManager] Queued interaction: ${interactionType} on ${componentId} for user ${userId}`
    );
  }

  /**
   * Get and clear queued interactions for a user
   */
  getInteractions(userId: string, limit?: number): QueuedInteraction[] {
    const queue = this.interactionQueue.get(userId);
    if (!queue || queue.length === 0) {
      return [];
    }

    // Get interactions (optionally limited)
    const count = limit ? Math.min(limit, queue.length) : queue.length;
    const interactions = queue.splice(0, count);

    console.log(
      `[WebSocketManager] Retrieved ${interactions.length} interactions for user ${userId}`
    );

    return interactions;
  }

  /**
   * Check if user has pending interactions
   */
  hasInteractions(userId: string): boolean {
    const queue = this.interactionQueue.get(userId);
    return queue !== undefined && queue.length > 0;
  }

  // ============================================================================
  // Diagnostics
  // ============================================================================

  /**
   * Get connection statistics
   */
  getStats(): {
    totalClients: number;
    clientsByType: Record<string, number>;
    totalUsers: number;
    totalTopics: number;
    totalQueuedInteractions: number;
  } {
    const clientsByType: Record<string, number> = {};
    for (const { info } of this.clients.values()) {
      clientsByType[info.clientType] = (clientsByType[info.clientType] || 0) + 1;
    }

    let totalQueuedInteractions = 0;
    for (const queue of this.interactionQueue.values()) {
      totalQueuedInteractions += queue.length;
    }

    return {
      totalClients: this.clients.size,
      clientsByType,
      totalUsers: this.userToClients.size,
      totalTopics: this.topicToClients.size,
      totalQueuedInteractions,
    };
  }

  /**
   * Get client info by ID
   */
  getClientInfo(clientId: string): ClientInfo | undefined {
    return this.clients.get(clientId)?.info;
  }
}

// Singleton instance
let managerInstance: WebSocketManager | null = null;

/**
 * Get the WebSocket manager singleton
 */
export function getWebSocketManager(): WebSocketManager {
  if (!managerInstance) {
    managerInstance = new WebSocketManager();
  }
  return managerInstance;
}

// Re-export the class for typing
export { WebSocketManager };
