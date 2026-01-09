/**
 * Session Manager
 *
 * Manages sessions and clients for the unified WebSocket server.
 * A session groups all clients (browser, CLI) that share the same agent context.
 */

import type {
  Session,
  Client,
  ClientType,
  ServerToClientMessage,
  QueuedInteraction,
} from './types';

// ============================================================================
// Session Registry
// ============================================================================

const sessions = new Map<string, Session>();
const clientToSession = new Map<string, string>(); // clientId -> sessionId

// ============================================================================
// Interaction Queue (for agent to poll)
// ============================================================================

const interactionQueue: QueuedInteraction[] = [];
const MAX_QUEUE_SIZE = 100;
const INTERACTION_TTL_MS = 5 * 60 * 1000; // 5 minutes

// ============================================================================
// Session Management
// ============================================================================

/**
 * Create a new session for a user
 */
export function createSession(userId: string, sessionId?: string): Session {
  const id = sessionId || `session-${userId}-${Date.now()}`;

  // Check if session already exists
  const existing = sessions.get(id);
  if (existing) {
    return existing;
  }

  const session: Session = {
    id,
    userId,
    clients: new Map(),
    createdAt: Date.now(),
  };

  sessions.set(id, session);
  console.log(`[Session Manager] Created session: ${id} for user: ${userId}`);

  return session;
}

/**
 * Get a session by ID
 */
export function getSession(sessionId: string): Session | undefined {
  return sessions.get(sessionId);
}

/**
 * Get or create a session
 */
export function getOrCreateSession(userId: string, sessionId?: string): Session {
  if (sessionId) {
    const existing = sessions.get(sessionId);
    if (existing) {
      return existing;
    }
  }
  return createSession(userId, sessionId);
}

/**
 * Delete a session and disconnect all clients
 */
export function deleteSession(sessionId: string): void {
  const session = sessions.get(sessionId);
  if (!session) return;

  // Close all client connections
  for (const client of session.clients.values()) {
    try {
      client.ws.close(1000, 'Session ended');
    } catch (e) {
      // Ignore close errors
    }
    clientToSession.delete(client.id);
  }

  sessions.delete(sessionId);
  console.log(`[Session Manager] Deleted session: ${sessionId}`);
}

/**
 * Get all sessions (for health check)
 */
export function getAllSessions(): Session[] {
  return Array.from(sessions.values());
}

// ============================================================================
// Client Management
// ============================================================================

/**
 * Add a client to a session
 */
export function joinSession(
  sessionId: string,
  clientId: string,
  clientType: ClientType,
  ws: WebSocket
): Client | null {
  const session = sessions.get(sessionId);
  if (!session) {
    console.error(`[Session Manager] Session not found: ${sessionId}`);
    return null;
  }

  const client: Client = {
    id: clientId,
    type: clientType,
    ws,
    connectedAt: Date.now(),
    sessionId,
  };

  session.clients.set(clientId, client);
  clientToSession.set(clientId, sessionId);

  console.log(
    `[Session Manager] Client ${clientId} (${clientType}) joined session ${sessionId} ` +
      `(total clients: ${session.clients.size})`
  );

  return client;
}

/**
 * Remove a client from its session
 */
export function leaveSession(clientId: string): { sessionId: string; clientType: ClientType } | null {
  const sessionId = clientToSession.get(clientId);
  if (!sessionId) return null;

  const session = sessions.get(sessionId);
  if (!session) {
    clientToSession.delete(clientId);
    return null;
  }

  const client = session.clients.get(clientId);
  const clientType = client?.type || 'browser';

  session.clients.delete(clientId);
  clientToSession.delete(clientId);

  console.log(
    `[Session Manager] Client ${clientId} left session ${sessionId} ` +
      `(remaining clients: ${session.clients.size})`
  );

  // Clean up empty sessions after a delay
  if (session.clients.size === 0) {
    setTimeout(() => {
      const s = sessions.get(sessionId);
      if (s && s.clients.size === 0) {
        deleteSession(sessionId);
      }
    }, 60000); // 1 minute grace period
  }

  return { sessionId, clientType };
}

/**
 * Get a client by ID
 */
export function getClient(clientId: string): Client | undefined {
  const sessionId = clientToSession.get(clientId);
  if (!sessionId) return undefined;

  const session = sessions.get(sessionId);
  return session?.clients.get(clientId);
}

/**
 * Get session for a client
 */
export function getSessionForClient(clientId: string): Session | undefined {
  const sessionId = clientToSession.get(clientId);
  if (!sessionId) return undefined;
  return sessions.get(sessionId);
}

/**
 * Get all clients in a session
 */
export function getClientsInSession(sessionId: string): Client[] {
  const session = sessions.get(sessionId);
  if (!session) return [];
  return Array.from(session.clients.values());
}

/**
 * Check if CLI is connected in a session
 */
export function isCliConnected(sessionId: string): boolean {
  const session = sessions.get(sessionId);
  if (!session) return false;

  for (const client of session.clients.values()) {
    if (client.type === 'cli') return true;
  }
  return false;
}

// ============================================================================
// Message Broadcasting
// ============================================================================

/**
 * Broadcast a message to all clients in a session
 */
export function broadcastToSession(
  sessionId: string,
  message: ServerToClientMessage,
  excludeClientId?: string
): void {
  const session = sessions.get(sessionId);
  if (!session) return;

  const messageStr = JSON.stringify(message);

  for (const client of session.clients.values()) {
    if (client.id === excludeClientId) continue;

    try {
      if (client.ws.readyState === WebSocket.OPEN) {
        client.ws.send(messageStr);
      }
    } catch (error) {
      console.error(`[Session Manager] Failed to send to client ${client.id}:`, error);
    }
  }
}

/**
 * Send a message to a specific client
 */
export function sendToClient(clientId: string, message: ServerToClientMessage): void {
  const client = getClient(clientId);
  if (!client) return;

  try {
    if (client.ws.readyState === WebSocket.OPEN) {
      client.ws.send(JSON.stringify(message));
    }
  } catch (error) {
    console.error(`[Session Manager] Failed to send to client ${clientId}:`, error);
  }
}

// ============================================================================
// World Context Management
// ============================================================================

/**
 * Update world context for a session
 */
export function updateSessionContext(
  sessionId: string,
  context: { worldId?: string; storyId?: string; worldName?: string }
): void {
  const session = sessions.get(sessionId);
  if (!session) return;

  session.worldContext = {
    ...session.worldContext,
    ...context,
  };

  console.log(`[Session Manager] Updated context for session ${sessionId}:`, session.worldContext);
}

/**
 * Get world context for a session
 */
export function getSessionContext(sessionId: string): Session['worldContext'] {
  const session = sessions.get(sessionId);
  return session?.worldContext;
}

// ============================================================================
// Interaction Queue
// ============================================================================

/**
 * Queue an interaction from a client
 */
export function queueInteraction(
  sessionId: string,
  componentId: string,
  interactionType: string,
  data: any,
  target?: string
): void {
  const interaction: QueuedInteraction = {
    id: `int-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    timestamp: Date.now(),
    sessionId,
    componentId,
    interactionType,
    target,
    data,
  };

  interactionQueue.push(interaction);

  // Trim if too large
  while (interactionQueue.length > MAX_QUEUE_SIZE) {
    interactionQueue.shift();
  }

  console.log(
    `[Session Manager] Queued interaction: ${interactionType} on ${componentId} for session ${sessionId}`
  );
}

/**
 * Get interactions for a session (clears them)
 */
export function getInteractions(sessionId: string): QueuedInteraction[] {
  const now = Date.now();
  const validInteractions: QueuedInteraction[] = [];
  const remaining: QueuedInteraction[] = [];

  for (const interaction of interactionQueue) {
    if (now - interaction.timestamp >= INTERACTION_TTL_MS) {
      continue; // Expired, skip
    }

    if (interaction.sessionId === sessionId) {
      validInteractions.push(interaction);
    } else {
      remaining.push(interaction);
    }
  }

  // Replace queue with remaining interactions
  interactionQueue.length = 0;
  interactionQueue.push(...remaining);

  return validInteractions;
}

/**
 * Peek at interactions without clearing
 */
export function peekInteractions(sessionId: string): QueuedInteraction[] {
  const now = Date.now();
  return interactionQueue.filter(
    (i) => i.sessionId === sessionId && now - i.timestamp < INTERACTION_TTL_MS
  );
}

// ============================================================================
// Health Check
// ============================================================================

export function getHealthStatus(): {
  sessions: number;
  clients: number;
  interactions: number;
  sessionDetails: Array<{
    id: string;
    userId: string;
    clientCount: number;
    clients: Array<{ id: string; type: ClientType }>;
  }>;
} {
  const sessionDetails = Array.from(sessions.values()).map((s) => ({
    id: s.id,
    userId: s.userId,
    clientCount: s.clients.size,
    clients: Array.from(s.clients.values()).map((c) => ({ id: c.id, type: c.type })),
  }));

  return {
    sessions: sessions.size,
    clients: clientToSession.size,
    interactions: interactionQueue.length,
    sessionDetails,
  };
}
