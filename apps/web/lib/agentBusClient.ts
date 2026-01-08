/**
 * WebSocket Client - Canvas side
 *
 * Connects to the Next.js WebSocket server for real-time communication
 * between agents and the Canvas UI.
 *
 * This client is used by the browser to:
 * - Receive canvas_ui updates from agents
 * - Receive state_change notifications
 * - Receive suggestions from agents
 * - Send user interactions back to the server
 */

import type { ComponentSpec } from '@/components/canvas/types';
import type {
  ServerMessage,
  CanvasUpdateMessage,
  StateChangeMessage,
  SuggestionMessage,
  InteractionMessage,
  ClientIdentifyMessage,
  SubscribeMessage,
  PingMessage,
} from './websocket/types';

export interface AgentUIComponent {
  componentId: string;
  target: string;
  spec: ComponentSpec;
  mode: 'overlay' | 'fullscreen' | 'inline';
}

export interface WebSocketClientOptions {
  url?: string;
  userId?: string;
  sessionId?: string;
  onCanvasUpdate?: (
    componentId: string,
    target: string,
    action: 'create' | 'update' | 'remove',
    spec?: ComponentSpec,
    mode?: 'overlay' | 'fullscreen' | 'inline'
  ) => void;
  onStateChange?: (
    event: StateChangeMessage['event'],
    data: StateChangeMessage['data']
  ) => void;
  onSuggestion?: (suggestion: SuggestionMessage['payload']) => void;
  onConnect?: (clientId: string) => void;
  onDisconnect?: () => void;
  onError?: (error: string) => void;
}

/**
 * Get the WebSocket URL for the current environment
 */
function getDefaultWebSocketUrl(): string {
  if (typeof window === 'undefined') {
    return 'ws://localhost:3000/ws';
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host;
  return `${protocol}//${host}/ws`;
}

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private clientId: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private options: WebSocketClientOptions;

  constructor(options: WebSocketClientOptions = {}) {
    this.url = options.url || getDefaultWebSocketUrl();
    this.options = options;

    // Add query params for initial identification
    const params = new URLSearchParams();
    params.set('type', 'canvas');
    if (options.userId) params.set('userId', options.userId);
    if (options.sessionId) params.set('sessionId', options.sessionId);

    this.url = `${this.url}?${params.toString()}`;
  }

  connect(): void {
    console.log('[WebSocket] Connecting to', this.url);

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected');
        this.reconnectAttempts = 0;
        this.startPingInterval();
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as ServerMessage;
          this.handleMessage(message);
        } catch (err) {
          console.error('[WebSocket] Failed to parse message:', err);
        }
      };

      this.ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        this.stopPingInterval();
        this.options.onDisconnect?.();
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        this.options.onError?.('WebSocket connection error');
      };
    } catch (err) {
      console.error('[WebSocket] Failed to create connection:', err);
      this.options.onError?.('Failed to connect to WebSocket server');
    }
  }

  private startPingInterval(): void {
    this.stopPingInterval();
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        const ping: PingMessage = {
          type: 'ping',
          timestamp: Date.now(),
        };
        this.ws.send(JSON.stringify(ping));
      }
    }, 30000); // 30 second keepalive
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    console.log(
      `[WebSocket] Reconnecting in ${this.reconnectDelay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
    );

    setTimeout(() => {
      this.connect();
    }, this.reconnectDelay);
  }

  private handleMessage(message: ServerMessage): void {
    console.log('[WebSocket] Received:', message.type);

    switch (message.type) {
      case 'connection_ack':
        this.clientId = message.clientId;
        console.log('[WebSocket] Assigned ID:', this.clientId);
        this.options.onConnect?.(this.clientId);
        break;

      case 'canvas_update':
        this.handleCanvasUpdate(message);
        break;

      case 'state_change':
        this.handleStateChange(message);
        break;

      case 'suggestion':
        this.handleSuggestion(message);
        break;

      case 'error':
        console.error('[WebSocket] Error:', message.error, message.details);
        this.options.onError?.(message.error);
        break;

      case 'pong':
        // Keepalive response - no action needed
        break;
    }
  }

  private handleCanvasUpdate(message: CanvasUpdateMessage): void {
    const { action, target, componentId, spec, mode } = message;
    console.log(
      `[WebSocket] canvas_update: ${action} ${componentId} at ${target} (mode: ${mode})`
    );
    this.options.onCanvasUpdate?.(componentId, target, action, spec, mode || 'overlay');
  }

  private handleStateChange(message: StateChangeMessage): void {
    const { event, data } = message;
    console.log(`[WebSocket] state_change: ${event}`, data);
    this.options.onStateChange?.(event, data);
  }

  private handleSuggestion(message: SuggestionMessage): void {
    const { payload } = message;
    console.log(`[WebSocket] suggestion: ${payload.title}`, payload);
    this.options.onSuggestion?.(payload);
  }

  /**
   * Send user interaction to server
   */
  sendInteraction(
    componentId: string,
    interactionType: string,
    data: unknown,
    target?: string
  ): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[WebSocket] Not connected, cannot send interaction');
      return;
    }

    const message: InteractionMessage = {
      type: 'interaction',
      componentId,
      interactionType,
      data,
      target,
    };

    console.log('[WebSocket] Sending interaction:', message);
    this.ws.send(JSON.stringify(message));
  }

  /**
   * Identify client with additional context
   */
  identify(userId: string, sessionId?: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[WebSocket] Not connected, cannot identify');
      return;
    }

    const message: ClientIdentifyMessage = {
      type: 'identify',
      clientType: 'canvas',
      userId,
      sessionId,
    };

    console.log('[WebSocket] Identifying as:', userId);
    this.ws.send(JSON.stringify(message));
  }

  /**
   * Subscribe to topics for filtered updates
   */
  subscribe(topics: string[]): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[WebSocket] Not connected, cannot subscribe');
      return;
    }

    const message: SubscribeMessage = {
      type: 'subscribe',
      topics,
    };

    console.log('[WebSocket] Subscribing to:', topics);
    this.ws.send(JSON.stringify(message));
  }

  disconnect(): void {
    this.stopPingInterval();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  getClientId(): string | null {
    return this.clientId;
  }
}

// Legacy alias for backwards compatibility
export const AgentBusClient = WebSocketClient;
export type AgentBusClientOptions = WebSocketClientOptions;
