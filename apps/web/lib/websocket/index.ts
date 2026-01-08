/**
 * WebSocket Module Exports
 *
 * Unified exports for WebSocket functionality.
 */

// Types
export * from './types';

// Manager (singleton)
export { getWebSocketManager, WebSocketManager } from './manager';

// Server setup
export {
  initializeWebSocketServer,
  getWebSocketServer,
  shutdownWebSocketServer,
} from './server';
