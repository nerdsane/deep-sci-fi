import { z } from 'zod';
import { router, protectedProcedure } from '../trpc';
import { getLettaOrchestrator } from '@deep-sci-fi/letta';

/**
 * Agent management router
 * Handles creation and management of world and story agents
 */
export const agentsRouter = router({
  /**
   * Create a world agent for a world
   */
  createWorldAgent: protectedProcedure
    .input(z.object({
      worldId: z.string(),
    }))
    .mutation(async ({ ctx, input }) => {
      // Get world from database
      const world = await ctx.db.world.findUnique({
        where: { id: input.worldId },
      });

      if (!world) {
        throw new Error('World not found');
      }

      // Check ownership or collaboration
      if (world.ownerId !== ctx.session.user.id) {
        const hasAccess = await ctx.db.worldCollaborator.findFirst({
          where: {
            worldId: input.worldId,
            userId: ctx.session.user.id,
          },
        });

        if (!hasAccess) {
          throw new Error('Unauthorized');
        }
      }

      // Create agent via Letta Orchestrator
      const orchestrator = getLettaOrchestrator();
      const agentId = await orchestrator.createWorldAgent(world);

      // Update world with agent ID
      await ctx.db.world.update({
        where: { id: input.worldId },
        data: { worldAgentId: agentId },
      });

      return { agentId };
    }),

  /**
   * Create a story agent for a story
   */
  createStoryAgent: protectedProcedure
    .input(z.object({
      storyId: z.string(),
    }))
    .mutation(async ({ ctx, input }) => {
      // Get story and associated world
      const story = await ctx.db.story.findUnique({
        where: { id: input.storyId },
        include: {
          world: true,
        },
      });

      if (!story) {
        throw new Error('Story not found');
      }

      // Check ownership
      if (story.authorId !== ctx.session.user.id) {
        throw new Error('Unauthorized');
      }

      // Ensure world agent exists
      if (!story.world.worldAgentId) {
        // Create world agent first
        const orchestrator = getLettaOrchestrator();
        const worldAgentId = await orchestrator.createWorldAgent(story.world);

        await ctx.db.world.update({
          where: { id: story.worldId },
          data: { worldAgentId },
        });

        story.world.worldAgentId = worldAgentId;
      }

      // Create story agent via Letta Orchestrator
      const orchestrator = getLettaOrchestrator();
      const agentId = await orchestrator.createStoryAgent(story, story.world);

      // Update story with agent ID
      await ctx.db.story.update({
        where: { id: input.storyId },
        data: { storyAgentId: agentId },
      });

      return { agentId };
    }),

  /**
   * Get agent status
   */
  getAgentStatus: protectedProcedure
    .input(z.object({
      agentId: z.string(),
    }))
    .query(async ({ ctx, input }) => {
      // TODO: Implement agent status check via Letta API
      // For now, just check if agent exists in database

      const world = await ctx.db.world.findFirst({
        where: { worldAgentId: input.agentId },
      });

      if (world) {
        return {
          exists: true,
          type: 'world',
          worldId: world.id,
        };
      }

      const story = await ctx.db.story.findFirst({
        where: { storyAgentId: input.agentId },
      });

      if (story) {
        return {
          exists: true,
          type: 'story',
          storyId: story.id,
        };
      }

      return {
        exists: false,
      };
    }),
});
