/**
 * Experience Agent
 *
 * Specialized agent for crafting immersive experiences through:
 * - Image generation for scenes, characters, and locations
 * - Dynamic Canvas UI components
 * - Multimedia asset management
 * - Proactive suggestions to enhance storytelling
 *
 * The World Agent delegates experience-crafting tasks to this agent.
 */

import Letta from '@letta-ai/letta-client';
import type { PrismaClient } from '@deep-sci-fi/db';
import { generateExperienceAgentSystemPrompt as generatePrompt } from '../prompts';
import {
  imageGeneratorTool,
  assetManagerTool,
  canvasUiTool,
  getCanvasInteractionsTool,
  sendSuggestionTool,
} from '../tools';

// ============================================================================
// Types
// ============================================================================

export interface ExperienceAgentContext {
  worldId: string;
  worldName: string;
  storyId?: string;
  storyTitle?: string;
}

export interface ExperienceAgentConfig {
  lettaClient: Letta;
  db: PrismaClient;
  userId: string;
}

// ============================================================================
// System Prompt
// ============================================================================

/**
 * Generate system prompt for Experience Agent
 * Uses the comprehensive prompt from prompts.ts
 */
export function generateExperienceAgentSystemPrompt(
  context: ExperienceAgentContext
): string {
  return generatePrompt(context);
}

// ============================================================================
// Memory Blocks
// ============================================================================

export function getExperienceAgentMemoryBlocks(context: ExperienceAgentContext) {
  return [
    {
      label: 'persona',
      value: `I am the Experience Agent for "${context.worldName}". I specialize in creating immersive visual and interactive experiences that bring this world to life. My tools include image generation, dynamic UI creation, asset management, and proactive suggestions. I work alongside the World Agent to craft experiences that enhance storytelling without overwhelming it.`,
      description: 'Agent identity and capabilities',
      limit: 2000,
    },
    {
      label: 'context',
      value: JSON.stringify(
        {
          worldId: context.worldId,
          worldName: context.worldName,
          storyId: context.storyId || null,
          storyTitle: context.storyTitle || null,
          lastUpdated: new Date().toISOString(),
        },
        null,
        2
      ),
      description: 'Current world and story context',
      limit: 2000,
    },
    {
      label: 'visual_style',
      value: JSON.stringify(
        {
          guidelines: 'Pending: Visual style to be established based on world aesthetic',
          colorPalette: [],
          artStyle: null,
          imageModels: {
            preferred: 'auto',
            fallback: 'dall-e-3',
          },
        },
        null,
        2
      ),
      description: 'Visual style guidelines for this world',
      limit: 2000,
    },
    {
      label: 'asset_library',
      value: JSON.stringify(
        {
          characters: [],
          locations: [],
          objects: [],
          backgrounds: [],
          lastSync: new Date().toISOString(),
        },
        null,
        2
      ),
      description: 'Index of available assets for this world',
      limit: 4000,
    },
  ];
}

// ============================================================================
// Experience Agent Tools (for Letta SDK registration)
// ============================================================================

export function getExperienceAgentTools() {
  // Return tool definitions imported at module level (ES6 imports)
  return [
    imageGeneratorTool,
    assetManagerTool,
    canvasUiTool,
    getCanvasInteractionsTool,
    sendSuggestionTool,
  ];
}

// ============================================================================
// Agent Cache (in-memory, could use Redis in production)
// ============================================================================

// Cache Experience Agent IDs by world ID to avoid recreation
const experienceAgentCache = new Map<string, {
  agentId: string;
  createdAt: number;
}>();

// Cache TTL: 1 hour (agents are stateful, so we want some persistence)
const CACHE_TTL_MS = 60 * 60 * 1000;

/**
 * Check if a cached agent is still valid
 */
function getCachedAgentId(worldId: string): string | null {
  const cached = experienceAgentCache.get(worldId);
  if (!cached) {
    return null;
  }

  // Check if cache has expired
  if (Date.now() - cached.createdAt > CACHE_TTL_MS) {
    experienceAgentCache.delete(worldId);
    return null;
  }

  return cached.agentId;
}

/**
 * Cache an agent ID for a world
 */
function cacheAgentId(worldId: string, agentId: string): void {
  experienceAgentCache.set(worldId, {
    agentId,
    createdAt: Date.now(),
  });
}

// ============================================================================
// Agent Creation
// ============================================================================

/** Server-side tool names for Experience Agent */
const SERVER_TOOL_NAMES = [
  'conversation_search',
  'search_trajectories',
  'assess_output_quality',
  'check_logical_consistency',
];

/** Cached tool names after registration (includes both server-side and client-side) */
let cachedExperienceToolNames: string[] | null = null;

/**
 * Register Experience Agent's client-side tools on Letta server
 * Similar to orchestrator's registerClientTools but for Experience Agent tools
 */
async function registerExperienceAgentTools(client: Letta): Promise<string[]> {
  if (cachedExperienceToolNames) return cachedExperienceToolNames;

  console.log('[ExperienceAgent] Registering client-side tools on server...');

  const clientTools = getExperienceAgentTools();
  const registeredNames: string[] = [];

  for (const tool of clientTools) {
    try {
      // Create Python stub that raises exception (execution happens client-side)
      const sourceCode = `def ${tool.name}(**kwargs):
    """${(tool.description || '').replace(/"/g, '\\"')}"""
    raise Exception("This tool executes client-side only")`;

      await client.tools.upsert({
        source_code: sourceCode,
        description: tool.description || `Client-side tool: ${tool.name}`,
        default_requires_approval: true,
        args_json_schema: tool.parameters,
      });

      registeredNames.push(tool.name);
      console.log(`  Registered: ${tool.name}`);
    } catch (error) {
      console.warn(`  Failed to register ${tool.name}:`, error instanceof Error ? error.message : error);
    }
  }

  // Combine with server-side tools
  cachedExperienceToolNames = [...SERVER_TOOL_NAMES, ...registeredNames];
  console.log(`[ExperienceAgent] Registered ${registeredNames.length} client-side tools`);

  return cachedExperienceToolNames;
}

export async function getOrCreateExperienceAgent(
  config: ExperienceAgentConfig,
  context: ExperienceAgentContext
): Promise<string> {
  const { lettaClient, db, userId } = config;

  // Check cache first
  const cachedAgentId = getCachedAgentId(context.worldId);
  if (cachedAgentId) {
    console.log(
      `[ExperienceAgent] Using cached agent for world ${context.worldName}: ${cachedAgentId}`
    );

    // Verify agent still exists on Letta server
    try {
      await lettaClient.agents.retrieve(cachedAgentId);
      return cachedAgentId;
    } catch (error) {
      // Agent no longer exists, remove from cache
      console.log(`[ExperienceAgent] Cached agent no longer exists, creating new one`);
      experienceAgentCache.delete(context.worldId);
    }
  }

  // Register client-side tools on server (idempotent, cached after first call)
  const allToolNames = await registerExperienceAgentTools(lettaClient);

  // Create new agent
  const systemPrompt = generateExperienceAgentSystemPrompt(context);
  const memoryBlocks = getExperienceAgentMemoryBlocks(context);

  try {
    // Create memory blocks
    const createdBlocks = await Promise.all(
      memoryBlocks.map(async (block) => {
        const created = await lettaClient.blocks.create({
          label: block.label,
          value: block.value,
          description: block.description,
          limit: block.limit,
        });
        return created.id;
      })
    );

    // Create the agent with ALL tools (server-side + client-side)
    const agent = await lettaClient.agents.create({
      agent_type: 'letta_v1_agent',
      name: `experience-${context.worldId.substring(0, 8)}`,
      description: `Experience Agent for world "${context.worldName}"`,
      system: systemPrompt,
      model: 'anthropic/claude-sonnet-4-20250514',
      embedding: 'openai/text-embedding-3-small',
      block_ids: createdBlocks.filter((id): id is string => id !== undefined),
      tools: allToolNames, // Both server-side AND client-side tools
      include_base_tools: false,
      parallel_tool_calls: true,
      tags: ['origin:deep-sci-fi', 'type:experience-agent', `world:${context.worldId}`],
    });

    if (!agent.id) {
      throw new Error('Failed to create Experience Agent - no ID returned');
    }

    // Cache the new agent ID
    cacheAgentId(context.worldId, agent.id);

    console.log(
      `[ExperienceAgent] Created for world ${context.worldName}: ${agent.id}`
    );

    return agent.id;
  } catch (error) {
    console.error('[ExperienceAgent] Creation failed:', error);
    throw new Error(
      `Failed to create Experience Agent: ${error instanceof Error ? error.message : String(error)}`
    );
  }
}
