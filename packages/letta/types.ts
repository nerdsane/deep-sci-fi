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
