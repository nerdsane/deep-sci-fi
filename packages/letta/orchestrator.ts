// TODO: Import actual Letta client when implementing
// import { Letta } from '@letta-ai/letta-client';
import type { World, Story, User } from '@deep-sci-fi/types';
import type {
  AgentMessage,
  ChatSession,
  AgentResponse,
} from './types';
import { generateUserAgentSystemPrompt, generateWorldSystemPrompt } from './prompts';

/**
 * LettaOrchestrator - Two-Tier Agent Management Service
 *
 * ARCHITECTURE:
 * - User Agent (Orchestrator): ONE per user - handles world creation and routing
 * - World Agents: ONE per world - handles world AND all stories in that world
 *
 * CURRENT STATUS: Stub implementation
 *
 * This class provides the architecture for the two-tier agent system but does not
 * yet have a complete integration with the @letta-ai/letta-client SDK.
 *
 * TODO: Implement actual Letta SDK integration
 * - Initialize Letta client in constructor
 * - Implement agent creation with proper SDK calls
 * - Implement tool registration
 * - Implement message sending and streaming
 * - Handle error cases and retries
 */
export class LettaOrchestrator {
  // TODO: Add Letta client when implementing
  // private client: Letta;
  private activeSessions: Map<string, ChatSession>;

  constructor(apiKey?: string, baseUrl?: string) {
    // TODO: Initialize Letta client with actual SDK
    // this.client = new Letta({
    //   apiKey: apiKey || process.env.LETTA_API_KEY,
    //   baseURL: baseUrl || process.env.LETTA_BASE_URL || 'http://localhost:8283',
    // });
    this.activeSessions = new Map();

    console.warn('LettaOrchestrator: Using stub implementation. Letta SDK integration not yet complete.');
  }

  /**
   * Get or create User Agent (Orchestrator) for a user
   * This is the equivalent of letta-code's createAgent() function
   *
   * User Agent is active when:
   * - User is at worlds list
   * - User has no worlds
   * - User is creating a new world
   *
   * TODO: Implement with @letta-ai/letta-client
   */
  async getOrCreateUserAgent(userId: string, user: User): Promise<string> {
    // Check if user already has an agent
    if (user.userAgentId) {
      console.log(`User Agent exists for user ${userId}: ${user.userAgentId}`);
      return user.userAgentId;
    }

    // Generate system prompt
    const systemPrompt = generateUserAgentSystemPrompt();

    // TODO: Create agent with Letta SDK
    // const agent = await this.client.agents.create({
    //   name: `user-agent-${userId}`,
    //   system: systemPrompt,
    //   tools: [
    //     'world_draft_generator',
    //     'list_worlds',
    //     'user_preferences'
    //   ],
    //   memory: {
    //     persona: userAgentPersona,
    //     human: {
    //       userId: user.id,
    //       name: user.name,
    //       preferences: user.preferences || {}
    //     },
    //     active_world: null
    //   }
    // });

    // TODO: Save agent ID to database
    // await db.user.update({
    //   where: { id: userId },
    //   data: { userAgentId: agent.id }
    // });

    throw new Error(
      'LettaOrchestrator.getOrCreateUserAgent: Not yet implemented. ' +
      'Need to integrate with @letta-ai/letta-client SDK. ' +
      'System prompt generated successfully for user: ' + user.email
    );
  }

  /**
   * Get or create World Agent for a specific world
   *
   * World Agent is active when:
   * - User is working in this specific world
   * - User is in a story that belongs to this world
   *
   * World Agent handles BOTH:
   * - World management (rules, elements, consistency)
   * - Story creation (all stories in this world)
   *
   * TODO: Implement with @letta-ai/letta-client
   */
  async getOrCreateWorldAgent(worldId: string, world: World): Promise<string> {
    // Check if world already has an agent
    if (world.worldAgentId) {
      console.log(`World Agent exists for world ${worldId}: ${world.worldAgentId}`);
      return world.worldAgentId;
    }

    // Generate system prompt
    const systemPrompt = generateWorldSystemPrompt(world);

    // TODO: Create agent with Letta SDK
    // const agent = await this.client.agents.create({
    //   name: `world-agent-${worldId}`,
    //   system: systemPrompt,
    //   tools: [
    //     'world_manager',
    //     'story_manager',
    //     'image_generator',
    //     'canvas_ui',
    //     'send_suggestion'
    //   ],
    //   memory: {
    //     persona: worldAgentPersona,
    //     project: world.foundation,
    //     human: await getUserPreferences(world.ownerId),
    //     current_story: null
    //   }
    // });

    // TODO: Save agent ID to database
    // await db.world.update({
    //   where: { id: worldId },
    //   data: { worldAgentId: agent.id }
    // });

    throw new Error(
      'LettaOrchestrator.getOrCreateWorldAgent: Not yet implemented. ' +
      'Need to integrate with @letta-ai/letta-client SDK. ' +
      'System prompt generated successfully for world: ' + world.name
    );
  }

  /**
   * Route message to appropriate agent based on context
   *
   * Routing logic:
   * - If worldId is present → route to World Agent
   * - If worldId is absent → route to User Agent (orchestrator)
   *
   * TODO: Implement with @letta-ai/letta-client
   */
  async sendMessage(
    userId: string,
    message: string,
    context: {
      worldId?: string;
      storyId?: string;
    }
  ): Promise<AgentResponse> {
    // TODO: Implement routing logic
    // if (context.worldId) {
    //   // Route to World Agent
    //   const world = await db.world.findUnique({ where: { id: context.worldId } });
    //   const worldAgentId = await this.getOrCreateWorldAgent(context.worldId, world);
    //
    //   // Set story context if in a story
    //   if (context.storyId) {
    //     const story = await db.story.findUnique({ where: { id: context.storyId } });
    //     await this.setStoryContext(worldAgentId, story);
    //   }
    //
    //   return await this.sendToAgent(worldAgentId, message);
    // }
    //
    // // Otherwise, route to User Agent (orchestrator)
    // const user = await db.user.findUnique({ where: { id: userId } });
    // const userAgentId = await this.getOrCreateUserAgent(userId, user);
    //
    // return await this.sendToAgent(userAgentId, message);

    throw new Error(
      'LettaOrchestrator.sendMessage: Not yet implemented. ' +
      'Need to integrate with @letta-ai/letta-client SDK for message routing. ' +
      'Context: ' + JSON.stringify(context)
    );
  }

  /**
   * Send message to a specific agent
   *
   * TODO: Implement with @letta-ai/letta-client
   */
  private async sendToAgent(agentId: string, message: string): Promise<AgentResponse> {
    // TODO: Send to actual Letta agent
    // const response = await this.client.agents.messages.send({
    //   agentId,
    //   message,
    //   streamSteps: true
    // });
    //
    // return this.parseResponse(response);

    throw new Error(
      'LettaOrchestrator.sendToAgent: Not yet implemented. ' +
      'Need to integrate with @letta-ai/letta-client SDK.'
    );
  }

  /**
   * Set story context in world agent memory
   * Updates the current_story memory block to give the agent context
   *
   * TODO: Implement with @letta-ai/letta-client
   */
  async setStoryContext(worldAgentId: string, story: Story): Promise<void> {
    // TODO: Update agent memory
    // await this.client.agents.blocks.update({
    //   agentId: worldAgentId,
    //   blockName: 'current_story',
    //   value: {
    //     storyId: story.id,
    //     title: story.title,
    //     description: story.description
    //   }
    // });

    console.log(`Set story context for agent ${worldAgentId}: ${story.title}`);
  }

  /**
   * Parse agent response (tool calls, messages, etc.)
   *
   * TODO: Implement actual response parsing
   */
  private parseResponse(response: any): AgentResponse {
    // TODO: Parse Letta SDK response
    return {
      messages: [],
      toolCalls: [],
      metadata: {},
    };
  }

  /**
   * Start a chat session with an agent
   * TODO: Implement actual session management
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
    console.log(`Started chat session ${sessionId} for agent ${agentId}`);
    return sessionId;
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
    console.log(`Ended chat session ${sessionId}`);
  }

  /**
   * Clean up resources
   */
  async cleanup(): Promise<void> {
    // End all active sessions
    this.activeSessions.clear();
    console.log('LettaOrchestrator: Cleaned up all sessions');
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
