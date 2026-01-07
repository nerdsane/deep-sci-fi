import type { World, Story } from '@deep-sci-fi/types';

export interface AgentConfig {
  id: string;
  name: string;
  type: 'world' | 'story';
  systemPrompt: string;
  tools: string[];
  memoryConfig: {
    coreMemory: Record<string, any>;
    archivalMemoryEnabled: boolean;
    recallMemoryEnabled: boolean;
  };
}

export interface WorldAgentConfig extends AgentConfig {
  type: 'world';
  worldId: string;
  world: World;
}

export interface StoryAgentConfig extends AgentConfig {
  type: 'story';
  storyId: string;
  worldId: string;
  story: Story;
}

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

export interface WorldQueryResult {
  rules: string[];
  constraints: string[];
  elements: any[];
  reasoning: string;
}

export interface AgentResponse {
  message: string;
  actions?: Array<{
    type: 'created_element' | 'updated_world' | 'generated_image' | 'checked_consistency' | 'created_vn_scene';
    data: any;
  }>;
  thoughtProcess?: string;
}
