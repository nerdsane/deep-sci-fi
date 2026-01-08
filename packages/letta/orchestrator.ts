import Letta from '@letta-ai/letta-client';
import type { PrismaClient } from '@deep-sci-fi/db';
import type { World, Story, User } from '@deep-sci-fi/db';
import type {
  AgentMessage,
  ChatSession,
  AgentResponse,
} from './types';
import { generateUserAgentSystemPrompt, generateWorldSystemPrompt } from './prompts';
import {
  getUserAgentMemoryBlocks,
  getWorldAgentMemoryBlocks,
} from './memory/blocks';
import {
  createMemoryBlocks,
  updateMemoryBlock,
  cacheMemoryBlocks,
} from './memory/manager';
import {
  getUserAgentClientTools,
  getWorldAgentClientTools,
  executeTool,
  type ToolContext,
} from './tools/executor';

/**
 * LettaOrchestrator - Two-Tier Agent Management Service
 *
 * ARCHITECTURE:
 * - User Agent (Orchestrator): ONE per user - handles world creation and routing
 * - World Agents: ONE per world - handles world AND all stories in that world
 *
 * This class provides the full implementation of the two-tier agent system
 * with complete integration with the @letta-ai/letta-client SDK.
 */
export class LettaOrchestrator {
  private client: Letta;
  private db: PrismaClient | null;
  private activeSessions: Map<string, ChatSession>;

  constructor(apiKey?: string, baseUrl?: string, db?: PrismaClient) {
    // Get API configuration from environment or parameters
    const lettaApiKey = apiKey || process.env.LETTA_API_KEY;
    const lettaBaseUrl = baseUrl || process.env.LETTA_BASE_URL || 'http://localhost:8283';

    // Check if using local Letta server (localhost or 127.0.0.1)
    const isLocalServer = lettaBaseUrl.includes('localhost') || lettaBaseUrl.includes('127.0.0.1');

    // Validate required configuration
    // API key is only required for Letta Cloud, not for local servers
    if (!lettaApiKey && !isLocalServer) {
      throw new Error(
        'LettaOrchestrator: LETTA_API_KEY is required for Letta Cloud. ' +
        'Set it via environment variable or pass as constructor parameter. ' +
        'For local Letta servers, no API key is needed.'
      );
    }

    // Initialize Letta client with custom headers for tracking
    // Use 'local-dev' placeholder for local servers without API key
    this.client = new Letta({
      apiKey: lettaApiKey || 'local-dev',
      baseURL: lettaBaseUrl,
      defaultHeaders: {
        'X-Letta-Source': 'deep-sci-fi',
        'User-Agent': 'deep-sci-fi/0.1.0',
      },
    });

    this.db = db || null;
    this.activeSessions = new Map();

    console.log(`LettaOrchestrator: Initialized with Letta SDK at ${lettaBaseUrl}`);
  }

  /**
   * Get or create User Agent (Orchestrator) for a user
   * This is the equivalent of letta-code's createAgent() function
   *
   * User Agent is active when:
   * - User is at worlds list
   * - User has no worlds
   * - User is creating a new world
   */
  async getOrCreateUserAgent(userId: string, user: User): Promise<string> {
    // Check if user already has an agent
    if (user.userAgentId) {
      console.log(`User Agent exists for user ${userId}: ${user.userAgentId}`);
      return user.userAgentId;
    }

    console.log(`Creating User Agent for user ${userId} (${user.email})`);

    // Generate system prompt
    const systemPrompt = generateUserAgentSystemPrompt();

    // Create memory blocks
    const memoryBlockDefinitions = getUserAgentMemoryBlocks({
      id: user.id,
      name: user.name,
      email: user.email,
    });

    const createdBlocks = await createMemoryBlocks(this.client, memoryBlockDefinitions);
    const blockIds = createdBlocks.map(b => b.id);

    // Create agent with Letta SDK
    // NOTE: We don't pass tool names here because we use client-side tools
    // Client tools are passed with each message, not registered with the agent
    const agent = await this.client.agents.create({
      agent_type: 'letta_v1_agent',
      system: systemPrompt,
      name: `user-agent-${userId}`,
      description: `Deep Sci-Fi User Agent (Orchestrator) for ${user.email}`,
      embedding: 'openai/text-embedding-3-small',
      model: 'anthropic/claude-opus-4-5-20251101',
      context_window_limit: 200000,
      tools: [], // No server-side tools, only client-side tools
      block_ids: blockIds,
      include_base_tools: false,
      parallel_tool_calls: true,
      enable_sleeptime: false,
      tags: ['origin:deep-sci-fi', 'type:user-agent'],
    });

    if (!agent.id) {
      throw new Error('Created User Agent has no ID');
    }

    console.log(`Created User Agent: ${agent.id} for user ${userId}`);

    // Save agent ID to database if db is available
    if (this.db) {
      await this.db.user.update({
        where: { id: userId },
        data: { userAgentId: agent.id },
      });

      // Cache memory blocks
      await cacheMemoryBlocks(this.db, agent.id, userId, null, createdBlocks);
    } else {
      console.warn('No database client available - agent ID not saved to database');
    }

    return agent.id;
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
   */
  async getOrCreateWorldAgent(worldId: string, world: World, owner: User): Promise<string> {
    // Check if world already has an agent
    if (world.worldAgentId) {
      console.log(`World Agent exists for world ${worldId}: ${world.worldAgentId}`);
      return world.worldAgentId;
    }

    console.log(`Creating World Agent for world ${worldId} (${world.name})`);

    // Generate system prompt
    const systemPrompt = generateWorldSystemPrompt(world);

    // Create memory blocks
    const memoryBlockDefinitions = getWorldAgentMemoryBlocks(
      {
        name: world.name,
        description: world.description,
        foundation: world.foundation,
      },
      {
        id: owner.id,
        name: owner.name,
        preferences: owner.preferences,
      }
    );

    const createdBlocks = await createMemoryBlocks(this.client, memoryBlockDefinitions);
    const blockIds = createdBlocks.map(b => b.id);

    // Create agent with Letta SDK
    // NOTE: We don't pass tool names here because we use client-side tools
    // Client tools are passed with each message, not registered with the agent
    const agent = await this.client.agents.create({
      agent_type: 'letta_v1_agent',
      system: systemPrompt,
      name: `world-agent-${worldId}`,
      description: `Deep Sci-Fi World Agent for "${world.name}" (${worldId})`,
      embedding: 'openai/text-embedding-3-small',
      model: 'anthropic/claude-opus-4-5-20251101',
      context_window_limit: 200000,
      tools: [], // No server-side tools, only client-side tools
      block_ids: blockIds,
      include_base_tools: false,
      parallel_tool_calls: true,
      enable_sleeptime: false,
      tags: ['origin:deep-sci-fi', 'type:world-agent', `world:${worldId}`],
    });

    if (!agent.id) {
      throw new Error('Created World Agent has no ID');
    }

    console.log(`Created World Agent: ${agent.id} for world ${worldId}`);

    // Save agent ID to database if db is available
    if (this.db) {
      await this.db.world.update({
        where: { id: worldId },
        data: { worldAgentId: agent.id },
      });

      // Cache memory blocks
      await cacheMemoryBlocks(this.db, agent.id, null, worldId, createdBlocks);
    } else {
      console.warn('No database client available - agent ID not saved to database');
    }

    return agent.id;
  }

  /**
   * Route message to appropriate agent based on context
   *
   * Routing logic:
   * - If worldId is present → route to World Agent
   * - If worldId is absent → route to User Agent (orchestrator)
   */
  async sendMessage(
    userId: string,
    message: string,
    context: {
      worldId?: string;
      storyId?: string;
    }
  ): Promise<AgentResponse> {
    if (!this.db) {
      throw new Error('Database client is required for sendMessage');
    }

    // If user is in a world, route to World Agent
    if (context.worldId) {
      const world = await this.db.world.findUnique({
        where: { id: context.worldId },
        include: { owner: true },
      });

      if (!world) {
        throw new Error(`World not found: ${context.worldId}`);
      }

      const worldAgentId = await this.getOrCreateWorldAgent(context.worldId, world, world.owner);

      // Set story context if in a story
      if (context.storyId) {
        const story = await this.db.story.findUnique({ where: { id: context.storyId } });
        if (!story) {
          throw new Error(`Story not found: ${context.storyId}`);
        }
        await this.setStoryContext(worldAgentId, story);
      }

      return await this.sendToAgent(worldAgentId, message, userId, 'world', {
        worldId: context.worldId,
        storyId: context.storyId,
        worldName: world.name,
      });
    }

    // Otherwise, route to User Agent (orchestrator)
    const user = await this.db.user.findUnique({ where: { id: userId } });
    if (!user) {
      throw new Error(`User not found: ${userId}`);
    }

    const userAgentId = await this.getOrCreateUserAgent(userId, user);
    return await this.sendToAgent(userAgentId, message, userId, 'user');
  }

  /**
   * Send message to a specific agent with streaming
   *
   * Implements full client-side tool execution with approval handling loop:
   * 1. Stream messages until stop_reason === "requires_approval"
   * 2. Execute all pending approval requests
   * 3. Send approval results back to Letta
   * 4. Continue streaming (repeat until stop_reason === "end_turn")
   */
  private async sendToAgent(
    agentId: string,
    message: string,
    userId: string,
    agentType: 'user' | 'world',
    worldContext?: {
      worldId: string;
      storyId?: string;
      worldName: string;
    }
  ): Promise<AgentResponse> {
    console.log(`Sending message to agent ${agentId} (${agentType}): ${message.substring(0, 50)}...`);

    if (!this.db) {
      throw new Error('Database client is required for tool execution');
    }

    // Get client tools based on agent type
    const clientTools = agentType === 'user'
      ? getUserAgentClientTools()
      : getWorldAgentClientTools();

    console.log(`Using ${clientTools.length} client tools for ${agentType} agent`);

    const messages: AgentMessage[] = [];
    const toolCalls: Array<{ name: string; args: any; result?: any }> = [];
    let thoughtProcess = '';

    // Current input for the loop (starts with user message, then becomes approval results)
    let currentInput: any = [{ role: 'user', content: message }];

    try {
      // Approval handling loop - continue until agent completes turn
      while (true) {
        // Accumulate approval requests from this stream
        const approvalRequests = new Map<string, { toolName: string; args: string }>();
        let stopReason: string | undefined;

        // Send message with streaming and client_tools
        const stream = await this.client.agents.messages.create(agentId, {
          messages: currentInput,
          streaming: true,
          stream_tokens: true,
          // Pass client tools so Letta knows about them
          client_tools: clientTools,
        });

        // Process stream chunks
        for await (const chunk of stream) {
          if (!chunk || typeof chunk !== 'object') {
            continue;
          }

          // Check for stop_reason
          if ('stop_reason' in chunk && typeof chunk.stop_reason === 'string') {
            stopReason = chunk.stop_reason;
            console.log('[Stop Reason]:', stopReason);
          }

          // Handle different message types
          if ('reasoning_message' in chunk && chunk.reasoning_message) {
            thoughtProcess += chunk.reasoning_message;
            console.log('[Reasoning]:', chunk.reasoning_message);
          } else if ('assistant_message' in chunk && chunk.assistant_message) {
            const assistantMsg = chunk.assistant_message as string;
            messages.push({
              role: 'agent',
              content: assistantMsg,
            });
            console.log('[Assistant]:', assistantMsg);
          } else if ('tool_call_message' in chunk && chunk.tool_call_message) {
            const toolCall = chunk.tool_call_message as { name?: string; arguments?: string };
            console.log('[Tool Call]:', toolCall.name, toolCall.arguments);
            toolCalls.push({
              name: toolCall.name || 'unknown',
              args: toolCall.arguments,
            });
          } else if ('tool_return_message' in chunk && chunk.tool_return_message) {
            const toolReturn = chunk.tool_return_message;
            console.log('[Tool Return]:', toolReturn);

            // Find the corresponding tool call and add the result
            const lastToolCall = toolCalls[toolCalls.length - 1];
            if (lastToolCall) {
              lastToolCall.result = toolReturn;
            }
          } else if ('approval_request_message' in chunk) {
            // Accumulate approval requests (stream-aware: accumulate by tool_call_id)
            const approvalChunk = chunk as any;
            const toolCall = approvalChunk.tool_call;

            if (toolCall?.tool_call_id && toolCall?.name) {
              const existing = approvalRequests.get(toolCall.tool_call_id);
              approvalRequests.set(toolCall.tool_call_id, {
                toolName: toolCall.name,
                args: (existing?.args || '') + (toolCall.arguments || ''),
              });
              console.log('[Approval Request]:', toolCall.name, 'for tool_call_id:', toolCall.tool_call_id);
            }
          }
        }

        // Stream complete - check stop reason
        console.log(`Stream complete. Stop reason: ${stopReason}, Approval requests: ${approvalRequests.size}`);

        // Case 1: Turn ended normally - break out of loop
        if (stopReason === 'end_turn') {
          break;
        }

        // Case 2: Requires approval - execute tools and continue
        if (stopReason === 'requires_approval') {
          if (approvalRequests.size === 0) {
            console.warn('Stop reason is requires_approval but no approval requests found');
            break;
          }

          // Execute all approval requests
          const approvalResults = [];

          for (const [toolCallId, { toolName, args }] of approvalRequests.entries()) {
            console.log(`Executing tool: ${toolName} (call_id: ${toolCallId})`);

            try {
              // Parse arguments
              const parsedArgs = args ? JSON.parse(args) : {};

              // Execute tool with full context
              const result = await executeTool(
                toolName,
                parsedArgs,
                {
                  userId,
                  db: this.db,
                  worldId: worldContext?.worldId,
                  storyId: worldContext?.storyId,
                  worldName: worldContext?.worldName,
                  lettaClient: this.client,
                }
              );

              console.log(`Tool ${toolName} completed successfully`);

              // Format result for Letta
              approvalResults.push({
                type: 'tool',
                tool_call_id: toolCallId,
                tool_return: JSON.stringify(result),
                status: 'success',
              });
            } catch (error) {
              console.error(`Tool ${toolName} failed:`, error);

              // Format error for Letta
              approvalResults.push({
                type: 'tool',
                tool_call_id: toolCallId,
                tool_return: `Error: ${error instanceof Error ? error.message : String(error)}`,
                status: 'error',
              });
            }
          }

          // Send approval results back to Letta and continue streaming
          currentInput = [{
            type: 'approval',
            approvals: approvalResults,
          }] as any;

          console.log(`Sending ${approvalResults.length} approval results back to agent`);

          // Continue loop to process the next stream
          continue;
        }

        // Other stop reasons - break
        console.log(`Unknown stop reason: ${stopReason} - ending loop`);
        break;
      }

      console.log(`Conversation complete. Messages: ${messages.length}, Tool calls: ${toolCalls.length}`);

      return {
        messages,
        toolCalls,
        metadata: {
          thoughtProcess,
        },
      };
    } catch (error) {
      console.error(`Failed to send message to agent ${agentId}:`, error);
      throw new Error(
        `Failed to send message to agent: ${
          error instanceof Error ? error.message : String(error)
        }`
      );
    }
  }

  /**
   * Set story context in world agent memory
   * Updates the current_story memory block to give the agent context
   */
  async setStoryContext(worldAgentId: string, story: Story): Promise<void> {
    console.log(`Setting story context for agent ${worldAgentId}: ${story.title}`);

    const storyContextValue = `# ${story.title}

Story ID: ${story.id}

${story.description || 'No description provided'}

## Story Progress
(Updated as story segments are created)

## Active Characters
(Populated from story segments)

## Current Scene
(Updated with latest segment)`;

    try {
      await updateMemoryBlock(
        this.client,
        worldAgentId,
        'current_story',
        storyContextValue
      );

      console.log(`Updated story context for agent ${worldAgentId}: ${story.title}`);
    } catch (error) {
      console.error(`Failed to set story context for agent ${worldAgentId}:`, error);
      throw new Error(
        `Failed to set story context: ${
          error instanceof Error ? error.message : String(error)
        }`
      );
    }
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

/**
 * Get or create singleton LettaOrchestrator instance
 *
 * @param db - Prisma client (optional, but recommended for database operations)
 * @returns LettaOrchestrator instance
 */
export function getLettaOrchestrator(db?: PrismaClient): LettaOrchestrator {
  if (!orchestratorInstance) {
    orchestratorInstance = new LettaOrchestrator(
      process.env.LETTA_API_KEY,
      process.env.LETTA_BASE_URL,
      db
    );
  } else if (db && !orchestratorInstance['db']) {
    // If instance exists but doesn't have a db client, update it
    orchestratorInstance['db'] = db;
  }
  return orchestratorInstance;
}
