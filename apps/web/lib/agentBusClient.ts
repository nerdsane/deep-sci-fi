/**
 * Agent Bus Client - Canvas side
 *
 * Connects to Agent Bus and handles bidirectional communication
 */

import type { AgentBusMessage, CanvasUIMessage, InteractionMessage, StateChangeMessage, SuggestionMessage } from '@/agent-bus/types';
import type { ComponentSpec } from '@/components/canvas/types';

export interface AgentUIComponent {
  componentId: string;
  target: string;
  spec: ComponentSpec;
  mode: 'overlay' | 'fullscreen' | 'inline';
}

export interface AgentBusClientOptions {
  url?: string;
  onCanvasUI?: (componentId: string, target: string, action: 'create' | 'update' | 'remove', spec?: ComponentSpec, mode?: 'overlay' | 'fullscreen' | 'inline') => void;
  onStateChange?: (event: StateChangeMessage['event'], data: StateChangeMessage['data']) => void;
  onSuggestion?: (suggestion: SuggestionMessage['payload']) => void;
  onConnect?: (clientId: string) => void;
  onDisconnect?: () => void;
  onError?: (error: string) => void;
}

export class AgentBusClient {
  private ws: WebSocket | null = null;
  private url: string;
  private clientId: string | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;
  private options: AgentBusClientOptions;

  constructor(options: AgentBusClientOptions = {}) {
    this.url = options.url || 'ws://localhost:8284/ws?type=canvas';
    this.options = options;
  }

  connect() {
    console.log('[Agent Bus Client] Connecting to', this.url);

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('[Agent Bus Client] Connected');
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data) as AgentBusMessage;
          this.handleMessage(message);
        } catch (err) {
          console.error('[Agent Bus Client] Failed to parse message:', err);
        }
      };

      this.ws.onclose = () => {
        console.log('[Agent Bus Client] Disconnected');
        this.options.onDisconnect?.();
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error('[Agent Bus Client] WebSocket error:', error);
        this.options.onError?.('WebSocket connection error');
      };
    } catch (err) {
      console.error('[Agent Bus Client] Failed to create WebSocket:', err);
      this.options.onError?.('Failed to connect to Agent Bus');
    }
  }

  private attemptReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[Agent Bus Client] Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    console.log(`[Agent Bus Client] Reconnecting in ${this.reconnectDelay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    setTimeout(() => {
      this.connect();
    }, this.reconnectDelay);
  }

  private handleMessage(message: AgentBusMessage) {
    console.log('[Agent Bus Client] Received:', message.type);

    switch (message.type) {
      case 'connect':
        this.clientId = message.clientId;
        console.log('[Agent Bus Client] Assigned ID:', this.clientId);
        this.options.onConnect?.(this.clientId);
        break;

      case 'canvas_ui':
        this.handleCanvasUI(message);
        break;

      case 'state_change':
        this.handleStateChange(message);
        break;

      case 'suggestion':
        this.handleSuggestion(message);
        break;

      case 'error':
        console.error('[Agent Bus Client] Error:', message.error, message.details);
        this.options.onError?.(message.error);
        break;
    }
  }

  private handleCanvasUI(message: CanvasUIMessage) {
    const { action, target, componentId, spec, mode } = message;
    console.log(`[Agent Bus Client] canvas_ui: ${action} ${componentId} at ${target} (mode: ${mode})`);
    this.options.onCanvasUI?.(componentId, target, action, spec, mode || 'overlay');
  }

  private handleStateChange(message: StateChangeMessage) {
    const { event, data } = message;
    console.log(`[Agent Bus Client] state_change: ${event}`, data);
    this.options.onStateChange?.(event, data);
  }

  private handleSuggestion(message: SuggestionMessage) {
    const { payload } = message;
    console.log(`[Agent Bus Client] suggestion: ${payload.title}`, payload);
    this.options.onSuggestion?.(payload);
  }

  /**
   * Send user interaction to agent
   */
  sendInteraction(componentId: string, interactionType: string, data: any, target?: string) {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[Agent Bus Client] WebSocket not connected, cannot send interaction');
      return;
    }

    const message: InteractionMessage = {
      type: 'interaction',
      componentId,
      interactionType,
      data,
      target,
    };

    console.log('[Agent Bus Client] Sending interaction:', message);
    this.ws.send(JSON.stringify(message));
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}
