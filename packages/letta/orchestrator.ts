import { Letta } from 'letta';
import type { World, Story } from '@deep-sci-fi/types';
import type {
  AgentConfig,
  WorldAgentConfig,
  StoryAgentConfig,
  AgentMessage,
  ChatSession,
  WorldQueryResult,
  AgentResponse,
} from './types';
import { generateWorldSystemPrompt, generateStorySystemPrompt } from './prompts';
import { createWorldQueryTool } from './tools/world-query';

export class LettaOrchestrator {
  private client: Letta;
  private activeSessions: Map<string, ChatSession>;
  private worldAgents: Map<string, string>; // worldId -> agentId
  private storyAgents: Map<string, string>; // storyId -> agentId

  constructor(apiKey?: string, baseUrl?: string) {
    this.client = new Letta({
      apiKey: apiKey || process.env.LETTA_API_KEY,
      baseURL: baseUrl || process.env.LETTA_BASE_URL || 'http://localhost:8283',
    });
    this.activeSessions = new Map();
    this.worldAgents = new Map();
    this.storyAgents = new Map();
  }

  /**
   * Create a world agent for managing world state and rules
   */
  async createWorldAgent(world: World): Promise<string> {
    const systemPrompt = generateWorldSystemPrompt(world);

    const agent = await this.client.agents.create({
      name: `world-agent-${world.id}`,
      system: systemPrompt,
      tools: [
        'update_world_rules',
        'check_consistency',
        'query_world_elements',
        'create_world_element',
      ],
      memory: {
        core_memory: {
          world_id: world.id,
          world_name: world.name,
          foundation: JSON.stringify(world.foundation),
          surface: JSON.stringify(world.surface),
          constraints: JSON.stringify(world.constraints || []),
        },
      },
    });

    this.worldAgents.set(world.id, agent.id);
    return agent.id;
  }

  /**
   * Create a story agent with read-only access to world context
   */
  async createStoryAgent(story: Story, world: World): Promise<string> {
    const systemPrompt = generateStorySystemPrompt(story, world);
    const worldAgentId = this.worldAgents.get(world.id);

    if (!worldAgentId) {
      throw new Error(`World agent not found for world ${world.id}. Create world agent first.`);
    }

    // Create custom world_query tool for this story agent
    const worldQueryTool = createWorldQueryTool(worldAgentId, this.client);

    const agent = await this.client.agents.create({
      name: `story-agent-${story.id}`,
      system: systemPrompt,
      tools: [
        'world_query', // Custom tool for querying world agent
        'create_story_segment',
        'generate_vn_scene',
        'create_ui_component',
        'check_story_consistency',
      ],
      memory: {
        core_memory: {
          story_id: story.id,
          story_title: story.title,
          world_id: world.id,
          world_name: world.name,
          // Read-only world context
          world_foundation: JSON.stringify(world.foundation),
          world_surface: JSON.stringify(world.surface),
        },
      },
    });

    // Register the world_query tool for this agent
    await this.client.tools.create({
      name: 'world_query',
      description: 'Query the world agent for rules, constraints, and elements. Use this before creating story content to ensure consistency.',
      parameters: {
        type: 'object',
        properties: {
          query_type: {
            type: 'string',
            enum: ['rules', 'elements', 'consistency_check'],
            description: 'Type of query to perform',
          },
          query: {
            type: 'string',
            description: 'Natural language query about world rules or elements',
          },
          context: {
            type: 'object',
            description: 'Optional context for the query (e.g., story element being created)',
          },
        },
        required: ['query_type', 'query'],
      },
      handler: worldQueryTool,
    });

    this.storyAgents.set(story.id, agent.id);
    return agent.id;
  }

  /**
   * Start a chat session with an agent
   */
  async startChatSession(
    userId: string,
    agentId: string,
    context: { worldId?: string; storyId?: string }
  ): Promise<string> {
    const sessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

    const session: ChatSession = {
      id: sessionId,
      agentId,
      userId,
      messages: [],
      context,
    };

    this.activeSessions.set(sessionId, session);
    return sessionId;
  }

  /**
   * Send a message to an agent in a chat session
   */
  async sendMessage(
    sessionId: string,
    message: string
  ): Promise<AgentResponse> {
    const session = this.activeSessions.get(sessionId);
    if (!session) {
      throw new Error(`Session ${sessionId} not found`);
    }

    // Add user message to session
    session.messages.push({
      role: 'user',
      content: message,
    });

    // Send to Letta agent
    const response = await this.client.agents.messages.send({
      agentId: session.agentId,
      message,
      streamSteps: false,
    });

    // Parse agent response
    const agentResponse = this.parseAgentResponse(response);

    // Add agent message to session
    session.messages.push({
      role: 'agent',
      content: agentResponse.message,
      metadata: {
        actions: agentResponse.actions,
      },
    });

    return agentResponse;
  }

  /**
   * Query world agent from story agent (world_query tool implementation)
   */
  async queryWorldAgent(
    worldAgentId: string,
    queryType: 'rules' | 'elements' | 'consistency_check',
    query: string,
    context?: any
  ): Promise<WorldQueryResult> {
    const response = await this.client.agents.messages.send({
      agentId: worldAgentId,
      message: `Query Type: ${queryType}\nQuery: ${query}\nContext: ${JSON.stringify(context || {})}`,
      streamSteps: false,
    });

    // Parse world agent response into structured result
    return this.parseWorldQueryResponse(response);
  }

  /**
   * Get chat session history
   */
  getSessionHistory(sessionId: string): AgentMessage[] | null {
    const session = this.activeSessions.get(sessionId);
    return session ? session.messages : null;
  }

  /**
   * End a chat session
   */
  endChatSession(sessionId: string): void {
    this.activeSessions.delete(sessionId);
  }

  /**
   * Parse Letta agent response into structured format
   */
  private parseAgentResponse(response: any): AgentResponse {
    // Extract message content
    const message = response.messages?.[0]?.content || '';

    // Extract actions from function calls
    const actions = response.function_calls?.map((call: any) => {
      return {
        type: this.mapFunctionToActionType(call.name),
        data: call.arguments,
      };
    }) || [];

    // Extract thought process from internal monologue
    const thoughtProcess = response.internal_monologue || undefined;

    return {
      message,
      actions,
      thoughtProcess,
    };
  }

  /**
   * Parse world query response into structured result
   */
  private parseWorldQueryResponse(response: any): WorldQueryResult {
    // TODO: Implement proper parsing based on Letta response format
    const content = response.messages?.[0]?.content || '';

    return {
      rules: [],
      constraints: [],
      elements: [],
      reasoning: content,
    };
  }

  /**
   * Map Letta function names to action types
   */
  private mapFunctionToActionType(functionName: string): string {
    const mapping: Record<string, string> = {
      create_world_element: 'created_element',
      update_world_rules: 'updated_world',
      generate_vn_scene: 'created_vn_scene',
      create_ui_component: 'created_element',
      check_consistency: 'checked_consistency',
      check_story_consistency: 'checked_consistency',
    };

    return mapping[functionName] || 'created_element';
  }

  /**
   * Get world agent ID by world ID
   */
  getWorldAgentId(worldId: string): string | undefined {
    return this.worldAgents.get(worldId);
  }

  /**
   * Get story agent ID by story ID
   */
  getStoryAgentId(storyId: string): string | undefined {
    return this.storyAgents.get(storyId);
  }

  /**
   * Clean up resources
   */
  async cleanup(): Promise<void> {
    // End all active sessions
    this.activeSessions.clear();

    // TODO: Optionally archive or delete agents
    // For now, we keep agents persistent
  }
}

// Singleton instance for server-side use
let orchestratorInstance: LettaOrchestrator | null = null;

export function getLettaOrchestrator(): LettaOrchestrator {
  if (!orchestratorInstance) {
    orchestratorInstance = new LettaOrchestrator();
  }
  return orchestratorInstance;
}
