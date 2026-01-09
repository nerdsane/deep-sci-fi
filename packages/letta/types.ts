/**
 * Letta Agent Type Definitions
 */

export interface AgentMessage {
  role: 'user' | 'agent' | 'system';
  content: string;
  metadata?: {
    action?: string;
    data?: any;
  };
}

export interface ChatSession {
  id: string;
  agentId: string;
  userId: string;
  messages: AgentMessage[];
  context: {
    worldId?: string;
    storyId?: string;
  };
}

export interface AgentResponse {
  messages: AgentMessage[];
  toolCalls?: Array<{
    name: string;
    args: any;
    result?: any;
  }>;
  metadata?: {
    thoughtProcess?: string;
    [key: string]: any;
  };
}

/**
 * Streaming chunk types for real-time SSE responses
 * Based on Letta API message types
 */
export type StreamChunkType =
  | 'reasoning'
  | 'reasoning_end'
  | 'tool_call'
  | 'tool_result'
  | 'assistant'
  | 'assistant_end'
  | 'error'
  | 'warning'
  | 'info'
  | 'done'
  | 'usage';

export interface StreamChunk {
  type: StreamChunkType;
  id?: string;
  content?: string;
  // Tool call specific
  toolCallId?: string;
  toolName?: string;
  toolArgs?: string;
  toolResult?: string;
  toolStatus?: 'pending' | 'running' | 'success' | 'error';
  // Usage statistics
  usage?: {
    promptTokens?: number;
    completionTokens?: number;
    totalTokens?: number;
  };
  // Stop reason
  stopReason?: string;
}
