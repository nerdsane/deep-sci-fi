/**
 * WebSocket Server Setup
 *
 * Attaches a WebSocket server to the Next.js HTTP server.
 * Handles the WebSocket protocol, message parsing, and connection lifecycle.
 */

import { WebSocketServer, WebSocket } from 'ws';
import type { Server as HTTPServer } from 'http';
import { getWebSocketManager } from './manager';
import type { ClientMessage, ConnectionAckMessage, ErrorMessage, PongMessage } from './types';

let wss: WebSocketServer | null = null;

/**
 * Initialize WebSocket server on the HTTP server
 *
 * @param server - The HTTP server instance (from Next.js custom server)
 * @param path - The WebSocket endpoint path (default: '/ws')
 */
export function initializeWebSocketServer(
  server: HTTPServer,
  path: string = '/ws'
): WebSocketServer {
  if (wss) {
    console.log('[WebSocket] Server already initialized');
    return wss;
  }

  wss = new WebSocketServer({
    server,
    path,
    clientTracking: true,
  });

  const manager = getWebSocketManager();

  wss.on('connection', (ws: WebSocket, request) => {
    // Generate client ID and register
    const clientId = manager.addClient(ws);

    // Parse query parameters for initial identification
    const url = new URL(request.url || '', `http://${request.headers.host}`);
    const clientType = (url.searchParams.get('type') as 'canvas' | 'debug') || 'canvas';
    const userId = url.searchParams.get('userId') || undefined;
    const sessionId = url.searchParams.get('sessionId') || undefined;

    // Identify client immediately if params provided
    if (clientType || userId) {
      manager.identifyClient(clientId, clientType, userId, sessionId);
    }

    // Send connection acknowledgment
    const ackMessage: ConnectionAckMessage = {
      type: 'connection_ack',
      clientId,
      serverTime: Date.now(),
    };
    ws.send(JSON.stringify(ackMessage));

    console.log(
      `[WebSocket] Client connected: ${clientId} (type: ${clientType}, user: ${userId || 'anonymous'})`
    );

    // Handle incoming messages
    ws.on('message', (data: Buffer | ArrayBuffer | Buffer[]) => {
      try {
        const messageStr = data.toString();
        const message = JSON.parse(messageStr) as ClientMessage;
        handleClientMessage(clientId, message, ws);
      } catch (error) {
        console.error(`[WebSocket] Failed to parse message from ${clientId}:`, error);
        const errorMessage: ErrorMessage = {
          type: 'error',
          error: 'Invalid message format',
          code: 'PARSE_ERROR',
        };
        ws.send(JSON.stringify(errorMessage));
      }
    });

    // Handle close
    ws.on('close', (code: number, reason: Buffer) => {
      console.log(
        `[WebSocket] Client disconnected: ${clientId} (code: ${code}, reason: ${reason.toString()})`
      );
      manager.removeClient(clientId);
    });

    // Handle errors
    ws.on('error', (error: Error) => {
      console.error(`[WebSocket] Error for client ${clientId}:`, error);
      manager.removeClient(clientId);
    });
  });

  wss.on('error', (error: Error) => {
    console.error('[WebSocket] Server error:', error);
  });

  console.log(`[WebSocket] Server initialized on path: ${path}`);

  return wss;
}

/**
 * Handle incoming client message
 */
function handleClientMessage(
  clientId: string,
  message: ClientMessage,
  ws: WebSocket
): void {
  const manager = getWebSocketManager();

  switch (message.type) {
    case 'identify': {
      manager.identifyClient(
        clientId,
        message.clientType,
        message.userId,
        message.sessionId
      );
      break;
    }

    case 'subscribe': {
      manager.subscribe(clientId, message.topics);
      break;
    }

    case 'unsubscribe': {
      manager.unsubscribe(clientId, message.topics);
      break;
    }

    case 'interaction': {
      manager.queueInteraction(
        clientId,
        message.componentId,
        message.interactionType,
        message.data,
        message.target
      );
      break;
    }

    case 'ping': {
      const pongMessage: PongMessage = {
        type: 'pong',
        timestamp: message.timestamp,
      };
      ws.send(JSON.stringify(pongMessage));
      break;
    }

    default: {
      console.warn(`[WebSocket] Unknown message type from ${clientId}:`, message);
    }
  }
}

/**
 * Get the WebSocket server instance
 */
export function getWebSocketServer(): WebSocketServer | null {
  return wss;
}

/**
 * Shutdown WebSocket server
 */
export function shutdownWebSocketServer(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (!wss) {
      resolve();
      return;
    }

    console.log('[WebSocket] Shutting down server...');

    // Close all connections
    wss.clients.forEach((client) => {
      client.close(1001, 'Server shutting down');
    });

    wss.close((err) => {
      if (err) {
        console.error('[WebSocket] Error during shutdown:', err);
        reject(err);
      } else {
        console.log('[WebSocket] Server shut down successfully');
        wss = null;
        resolve();
      }
    });
  });
}
