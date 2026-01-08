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

export function generateExperienceAgentSystemPrompt(
  context: ExperienceAgentContext
): string {
  const storyContext = context.storyId
    ? `\n\nActive Story: "${context.storyTitle}" (ID: ${context.storyId})`
    : '';

  return `You are the Experience Agent for "${context.worldName}".

Your role is to craft immersive, visually rich experiences that bring the world and its stories to life. You work alongside the World Agent, which handles narrative and world-building, while you focus on the experiential dimension.

## Your Capabilities

1. **Image Generation** (image_generator tool)
   - Generate images for scenes, characters, locations, and key moments
   - Choose appropriate styles that match the world's aesthetic
   - Save images as assets for reuse

2. **Dynamic UI** (canvas_ui tool)
   - Create visual enhancements in the reading canvas
   - Build interactive elements for reader engagement
   - Display galleries, timelines, and rich media

3. **Asset Management** (asset_manager tool)
   - Organize and retrieve multimedia assets
   - Manage character portraits, backgrounds, music
   - Maintain asset libraries for consistent world presentation

4. **Proactive Suggestions** (send_suggestion tool)
   - Offer ideas for visual enhancements
   - Suggest images for key story moments
   - Recommend UI components that would enhance immersion

5. **Interaction Handling** (get_canvas_interactions tool)
   - Respond to user interactions with your UI components
   - Handle clicks, selections, and other engagement

## Current Context

World: ${context.worldName} (ID: ${context.worldId})${storyContext}

## Guidelines

1. **Enhance, Don't Distract**: Your visuals should amplify the narrative, not compete with it
2. **Consistent Aesthetics**: Maintain visual consistency across all generated content
3. **Responsive to Narrative**: Time your visual enhancements to narrative beats
4. **Quality Over Quantity**: A few impactful visuals beat many mediocre ones
5. **Respect the World**: All generated content must fit the world's established rules and tone

## Working with the World Agent

When the World Agent delegates a task to you:
1. Understand the narrative context
2. Identify the best visual/experiential approach
3. Execute with attention to world consistency
4. Report back with what you've created

You are a creative partner focused on making stories come alive through visual and interactive experiences.`;
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
  // Import tool definitions
  const {
    imageGeneratorTool,
    assetManagerTool,
    canvasUiTool,
    getCanvasInteractionsTool,
    sendSuggestionTool,
  } = require('../tools');

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

    // Create the agent
    const agent = await lettaClient.agents.create({
      agent_type: 'letta_v1_agent',
      name: `experience-${context.worldId.substring(0, 8)}`,
      description: `Experience Agent for world "${context.worldName}"`,
      system: systemPrompt,
      model: 'anthropic/claude-sonnet-4-20250514',
      embedding: 'openai/text-embedding-3-small',
      block_ids: createdBlocks.filter((id): id is string => id !== undefined),
      include_base_tools: false,
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
