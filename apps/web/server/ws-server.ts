/**
 * Unified WebSocket Server
 *
 * Bun-based WebSocket server that handles bidirectional communication
 * between Browser (Chat + Canvas), CLI, and the Agent.
 *
 * Run with: bun run apps/web/server/ws-server.ts
 */

import type { ServerWebSocket } from 'bun';
import type {
  ClientType,
  ClientToServerMessage,
  ConnectMessage,
  ClientJoinedMessage,
  ClientLeftMessage,
  PongMessage,
} from './types';
import {
  getOrCreateSession,
  joinSession,
  leaveSession,
  getHealthStatus,
  broadcastToSession,
  getClientsInSession,
} from './session-manager';
import { handleMessage } from './message-handler';

// ============================================================================
// Configuration
// ============================================================================

const PORT = parseInt(process.env.WS_PORT || '8284', 10);
const DEFAULT_USER_ID = 'dev-user'; // In production, extract from auth

// ============================================================================
// WebSocket Data
// ============================================================================

interface WSData {
  clientId: string;
  clientType: ClientType;
  sessionId: string;
}

// ============================================================================
// Server
// ============================================================================

console.log(`[WS Server] Starting unified WebSocket server on port ${PORT}...`);

const server = Bun.serve<WSData>({
  port: PORT,

  fetch(req, server) {
    const url = new URL(req.url);

    // Health check endpoint
    if (url.pathname === '/health') {
      const health = getHealthStatus();
      return new Response(JSON.stringify({ status: 'ok', ...health }), {
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // WebSocket upgrade
    if (url.pathname === '/ws') {
      // Parse query parameters
      const clientType = (url.searchParams.get('type') || 'browser') as ClientType;
      const sessionId = url.searchParams.get('sessionId') || `session-${DEFAULT_USER_ID}-default`;
      const userId = url.searchParams.get('userId') || DEFAULT_USER_ID;

      // Generate client ID
      const clientId = `${clientType}-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;

      // Ensure session exists
      getOrCreateSession(userId, sessionId);

      // Upgrade to WebSocket
      const success = server.upgrade(req, {
        data: {
          clientId,
          clientType,
          sessionId,
        },
      });

      if (success) {
        return undefined; // Bun handles the response
      }

      return new Response('WebSocket upgrade failed', { status: 500 });
    }

    // 404 for other paths
    return new Response('Not Found', { status: 404 });
  },

  websocket: {
    open(ws: ServerWebSocket<WSData>) {
      const { clientId, clientType, sessionId } = ws.data;

      console.log(`[WS Server] Client connected: ${clientId} (${clientType}) to session ${sessionId}`);

      // Join session
      const client = joinSession(sessionId, clientId, clientType, ws as unknown as WebSocket);

      if (!client) {
        ws.close(1011, 'Failed to join session');
        return;
      }

      // Get list of other clients in session
      const otherClients = getClientsInSession(sessionId)
        .filter((c) => c.id !== clientId)
        .map((c) => ({ id: c.id, type: c.type }));

      // Send connection confirmation to this client
      const connectMessage: ConnectMessage = {
        type: 'connect',
        clientId,
        sessionId,
        connectedClients: otherClients,
      };
      ws.send(JSON.stringify(connectMessage));

      // Notify other clients that this client joined
      const joinedMessage: ClientJoinedMessage = {
        type: 'client_joined',
        client: { id: clientId, type: clientType },
      };
      broadcastToSession(sessionId, joinedMessage, clientId);
    },

    async message(ws: ServerWebSocket<WSData>, message: string | Buffer) {
      const { clientId, clientType, sessionId } = ws.data;

      try {
        const data = JSON.parse(message.toString()) as ClientToServerMessage;

        // Handle ping/pong at server level
        if (data.type === 'ping') {
          const pong: PongMessage = { type: 'pong' };
          ws.send(JSON.stringify(pong));
          return;
        }

        // Get session
        const session = await import('./session-manager').then((m) => m.getSession(sessionId));
        if (!session) {
          ws.send(JSON.stringify({ type: 'error', error: 'Session not found' }));
          return;
        }

        // Get client
        const client = session.clients.get(clientId);
        if (!client) {
          ws.send(JSON.stringify({ type: 'error', error: 'Client not found in session' }));
          return;
        }

        // Handle the message
        await handleMessage(session, client, data);

      } catch (error) {
        console.error(`[WS Server] Error processing message from ${clientId}:`, error);
        ws.send(JSON.stringify({
          type: 'error',
          error: error instanceof Error ? error.message : 'Failed to process message',
        }));
      }
    },

    close(ws: ServerWebSocket<WSData>, code: number, reason: string) {
      const { clientId, clientType, sessionId } = ws.data;

      console.log(`[WS Server] Client disconnected: ${clientId} (code: ${code}, reason: ${reason})`);

      // Leave session
      const result = leaveSession(clientId);

      if (result) {
        // Notify other clients that this client left
        const leftMessage: ClientLeftMessage = {
          type: 'client_left',
          clientId,
          clientType,
        };
        broadcastToSession(result.sessionId, leftMessage);
      }
    },
  },
});

console.log(`[WS Server] Listening on ws://localhost:${PORT}/ws`);
console.log(`[WS Server] Health check: http://localhost:${PORT}/health`);

// Handle graceful shutdown
process.on('SIGINT', () => {
  console.log('\n[WS Server] Shutting down...');
  server.stop();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\n[WS Server] Shutting down...');
  server.stop();
  process.exit(0);
});
