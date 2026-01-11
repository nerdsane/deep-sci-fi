/**
 * Unified WebSocket Client
 *
 * Browser client for connecting to the unified WebSocket server.
 * Handles both Chat and Canvas communication through a single connection.
 */

// ============================================================================
// Types (imported from server, but defined here for browser compatibility)
// ============================================================================

export type ClientType = 'browser' | 'cli';

export interface StreamChunk {
  type: 'reasoning' | 'reasoning_end' | 'tool_call' | 'tool_result' | 'assistant' | 'assistant_end' | 'error' | 'warning' | 'info' | 'done' | 'usage';
  id?: string;
  content?: string;
  toolCallId?: string;
  toolName?: string;
  toolArgs?: string;
  toolResult?: string;
  toolStatus?: 'pending' | 'running' | 'success' | 'error';
  usage?: {
    promptTokens?: number;
    completionTokens?: number;
    totalTokens?: number;
  };
  stopReason?: string;
}

export interface ComponentSpec {
  type: string;
  id?: string;
  props?: Record<string, any>;
  children?: ComponentSpec | ComponentSpec[];
}

export interface ConnectedClient {
  id: string;
  type: ClientType;
}

// Message types
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
  event: string;
  data: Record<string, any>;
}

export interface SuggestionPayload {
  id: string;
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  actionId: string;
  actionLabel?: string;
  actionData?: any;
}

export interface HistoryMessage {
  id: string;
  role: string;
  content: string;
  messageType: string;
  toolName?: string | null;
  toolArgs?: string | null;
  toolResult?: string | null;
  toolStatus?: string | null;
  createdAt: string;
}

// ============================================================================
// Client Options
// ============================================================================

export interface UnifiedWSClientOptions {
  url?: string;
  sessionId?: string;
  userId?: string;
  autoReconnect?: boolean;
  maxReconnectAttempts?: number;
  reconnectDelay?: number;
}

// ============================================================================
// UnifiedWSClient Class
// ============================================================================

export class UnifiedWSClient {
  private ws: WebSocket | null = null;
  private url: string;
  private sessionId: string;
  private userId: string;
  private clientId: string | null = null;
  private connectedClients: ConnectedClient[] = [];
  private autoReconnect: boolean;
  private maxReconnectAttempts: number;
  private reconnectDelay: number;
  private reconnectAttempts = 0;
  private isConnecting = false;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private pendingConnectResolvers: Array<() => void> = [];
  private pendingConnectRejecters: Array<(err: Error) => void> = [];

  // Callbacks
  public onConnect: ((clientId: string, sessionId: string, clients: ConnectedClient[]) => void) | null = null;
  public onDisconnect: (() => void) | null = null;
  public onError: ((error: string) => void) | null = null;
  public onChatChunk: ((chunk: StreamChunk) => void) | null = null;
  public onCanvasUI: ((message: CanvasUIMessage) => void) | null = null;
  public onStateChange: ((event: string, data: Record<string, any>) => void) | null = null;
  public onSuggestion: ((suggestion: SuggestionPayload) => void) | null = null;
  public onClientJoined: ((client: ConnectedClient) => void) | null = null;
  public onClientLeft: ((clientId: string, clientType: ClientType) => void) | null = null;
  // Cache for message history received before handler is set up
  private _cachedMessageHistory: HistoryMessage[] | null = null;
  private _onMessageHistory: ((messages: HistoryMessage[]) => void) | null = null;

  // Getter/setter for onMessageHistory that auto-flushes cached history
  get onMessageHistory(): ((messages: HistoryMessage[]) => void) | null {
    return this._onMessageHistory;
  }

  set onMessageHistory(handler: ((messages: HistoryMessage[]) => void) | null) {
    this._onMessageHistory = handler;
    // If we have cached history and a new handler is set, flush the cache
    if (handler && this._cachedMessageHistory) {
      console.log('[WS Client] Flushing cached message history:', this._cachedMessageHistory.length, 'messages');
      handler(this._cachedMessageHistory);
      this._cachedMessageHistory = null;
    }
  }

  constructor(options: UnifiedWSClientOptions = {}) {
    const wsHost = typeof window !== 'undefined'
      ? window.location.hostname
      : 'localhost';

    // Use environment variable if available, otherwise construct from hostname
    const defaultWsUrl = typeof window !== 'undefined' && (window as any).__NEXT_DATA__?.runtimeConfig?.NEXT_PUBLIC_WS_URL
      ? (window as any).__NEXT_DATA__.runtimeConfig.NEXT_PUBLIC_WS_URL
      : process.env.NEXT_PUBLIC_WS_URL || `ws://${wsHost}:8284/ws`;

    this.url = options.url || defaultWsUrl;
    this.sessionId = options.sessionId || this.generateSessionId();
    this.userId = options.userId || 'dev-user';
    this.autoReconnect = options.autoReconnect ?? true;
    this.maxReconnectAttempts = options.maxReconnectAttempts ?? 10;
    this.reconnectDelay = options.reconnectDelay ?? 2000;
  }

  private generateSessionId(): string {
    // Use a stable session ID based on browser session
    if (typeof window !== 'undefined' && window.sessionStorage) {
      let sessionId = sessionStorage.getItem('dsf-session-id');
      if (!sessionId) {
        sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        sessionStorage.setItem('dsf-session-id', sessionId);
      }
      return sessionId;
    }
    return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  // ============================================================================
  // Connection Management
  // ============================================================================

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      // If already connected, resolve immediately
      if (this.ws?.readyState === WebSocket.OPEN) {
        resolve();
        return;
      }

      // If already connecting, queue this caller to be resolved when connection completes
      if (this.isConnecting) {
        this.pendingConnectResolvers.push(resolve);
        this.pendingConnectRejecters.push(reject);
        return;
      }

      this.isConnecting = true;
      this.pendingConnectResolvers.push(resolve);
      this.pendingConnectRejecters.push(reject);

      const fullUrl = `${this.url}?type=browser&sessionId=${this.sessionId}&userId=${this.userId}`;

      console.log('[WS Client] Connecting to', fullUrl);

      try {
        this.ws = new WebSocket(fullUrl);

        this.ws.onopen = () => {
          console.log('[WS Client] Connected');
          this.isConnecting = false;
          this.reconnectAttempts = 0;
          this.startPing();
          // Don't resolve yet - wait for connect message
        };

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            this.handleMessage(message);
          } catch (err) {
            console.error('[WS Client] Failed to parse message:', err);
          }
        };

        this.ws.onclose = (event) => {
          console.log('[WS Client] Disconnected', event.code, event.reason);
          this.isConnecting = false;
          this.stopPing();
          this.onDisconnect?.();

          if (this.autoReconnect && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.scheduleReconnect();
          }
        };

        this.ws.onerror = (event) => {
          console.error('[WS Client] WebSocket error:', event);
          this.isConnecting = false;
          this.onError?.('WebSocket connection error');
          // Reject all pending callers
          const error = new Error('WebSocket connection error');
          this.pendingConnectRejecters.forEach(rej => rej(error));
          this.pendingConnectResolvers = [];
          this.pendingConnectRejecters = [];
        };

      } catch (err) {
        this.isConnecting = false;
        console.error('[WS Client] Failed to create WebSocket:', err);
        // Reject all pending callers
        const error = err instanceof Error ? err : new Error(String(err));
        this.pendingConnectRejecters.forEach(rej => rej(error));
        this.pendingConnectResolvers = [];
        this.pendingConnectRejecters = [];
      }
    });
  }

  disconnect(): void {
    this.autoReconnect = false;
    this.stopPing();

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }

    this.clientId = null;
    this.connectedClients = [];
  }

  private scheduleReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);

    console.log(
      `[WS Client] Reconnecting in ${Math.round(delay)}ms ` +
      `(attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`
    );

    setTimeout(() => {
      if (this.autoReconnect) {
        this.connect().catch(() => {
          // Error already logged
        });
      }
    }, delay);
  }

  private startPing(): void {
    this.pingInterval = setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000); // Ping every 30 seconds
  }

  private stopPing(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  // ============================================================================
  // Message Handling
  // ============================================================================

  private handleMessage(message: any): void {
    switch (message.type) {
      case 'connect':
        this.clientId = message.clientId;
        this.connectedClients = message.connectedClients || [];
        console.log('[WS Client] Assigned ID:', this.clientId);
        console.log('[WS Client] Other clients:', this.connectedClients);
        if (this.clientId) {
          this.onConnect?.(this.clientId, message.sessionId, this.connectedClients);
        }
        // Resolve all pending connect() callers
        this.pendingConnectResolvers.forEach(res => res());
        this.pendingConnectResolvers = [];
        this.pendingConnectRejecters = [];
        break;

      case 'client_joined':
        this.connectedClients.push(message.client);
        console.log('[WS Client] Client joined:', message.client);
        this.onClientJoined?.(message.client);
        break;

      case 'client_left':
        this.connectedClients = this.connectedClients.filter((c) => c.id !== message.clientId);
        console.log('[WS Client] Client left:', message.clientId);
        this.onClientLeft?.(message.clientId, message.clientType);
        break;

      case 'chat_chunk':
        this.onChatChunk?.(message.chunk);
        break;

      case 'canvas_ui':
        this.onCanvasUI?.(message);
        break;

      case 'state_change':
        this.onStateChange?.(message.event, message.data);
        break;

      case 'suggestion':
        this.onSuggestion?.(message.payload);
        break;

      case 'error':
        console.error('[WS Client] Server error:', message.error, message.details);
        this.onError?.(message.error);
        break;

      case 'pong':
        // Heartbeat response, ignore
        break;

      case 'message_history':
        console.log('[WS Client] Received message history:', message.messages?.length, 'messages');
        if (this._onMessageHistory) {
          this._onMessageHistory(message.messages || []);
        } else {
          // Cache for later when handler is set up
          console.log('[WS Client] Caching message history for later');
          this._cachedMessageHistory = message.messages || [];
        }
        break;

      default:
        console.warn('[WS Client] Unknown message type:', message.type);
    }
  }

  // ============================================================================
  // Sending Messages
  // ============================================================================

  sendChatMessage(content: string, context?: { worldId?: string; storyId?: string }): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[WS Client] Cannot send - not connected');
      return;
    }

    const message = {
      type: 'chat_message',
      content,
      context,
    };

    console.log('[WS Client] Sending chat message:', content.substring(0, 50));
    this.ws.send(JSON.stringify(message));
  }

  sendInteraction(
    componentId: string,
    interactionType: string,
    data: any,
    target?: string
  ): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.warn('[WS Client] Cannot send - not connected');
      return;
    }

    const message = {
      type: 'interaction',
      componentId,
      interactionType,
      data,
      target,
    };

    console.log('[WS Client] Sending interaction:', interactionType, 'on', componentId);
    this.ws.send(JSON.stringify(message));
  }

  // ============================================================================
  // State Getters
  // ============================================================================

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  getClientId(): string | null {
    return this.clientId;
  }

  getSessionId(): string {
    return this.sessionId;
  }

  getConnectedClients(): ConnectedClient[] {
    return [...this.connectedClients];
  }

  isCliConnected(): boolean {
    return this.connectedClients.some((c) => c.type === 'cli');
  }
}

// ============================================================================
// Singleton Export (optional)
// ============================================================================

let defaultClient: UnifiedWSClient | null = null;

export function getDefaultWSClient(): UnifiedWSClient {
  if (!defaultClient) {
    defaultClient = new UnifiedWSClient();
  }
  return defaultClient;
}
