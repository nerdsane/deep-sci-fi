/**
 * Agent Bus - Message Protocol (Legacy)
 *
 * @deprecated Use @/lib/websocket/types instead
 *
 * This file re-exports types from the new websocket module for backwards compatibility.
 */

// Re-export all types from the new websocket module
export type {
  CanvasUpdateMessage as CanvasUIMessage,
  StateChangeMessage,
  InteractionMessage,
  SuggestionMessage,
  ErrorMessage,
  ConnectionAckMessage,
  ServerMessage,
  ClientMessage,
  WebSocketMessage as AgentBusMessage,
} from '../lib/websocket/types';

// Legacy ConnectionMessage type (deprecated)
export interface ConnectionMessage {
  type: 'connect' | 'disconnect';
  clientType: 'agent' | 'canvas';
  clientId: string;
}
