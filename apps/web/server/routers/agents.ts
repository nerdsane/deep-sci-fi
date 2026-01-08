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
   * NOTE: Agent creation is not yet fully implemented
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

      // TODO: Create agent via Letta Orchestrator
      // Currently throws "Not yet implemented" error
      throw new Error(
        'Agent creation not yet implemented. ' +
        'Letta SDK integration is in progress. ' +
        'World exists and can be used without an agent for now.'
      );

      // Future implementation:
      // const orchestrator = getLettaOrchestrator();
      // const agentId = await orchestrator.createWorldAgent(world);
      // await ctx.db.world.update({
      //   where: { id: input.worldId },
      //   data: { worldAgentId: agentId },
      // });
      // return { agentId };
    }),

  /**
   * Create a story agent for a story
   * NOTE: Agent creation is not yet fully implemented
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

      // TODO: Create story agent via Letta Orchestrator
      // Currently not implemented
      throw new Error(
        'Agent creation not yet implemented. ' +
        'Letta SDK integration is in progress. ' +
        'Story exists and can be used without an agent for now.'
      );

      // Future implementation:
      // Ensure world agent exists first
      // const orchestrator = getLettaOrchestrator();
      // if (!story.world.worldAgentId) {
      //   const worldAgentId = await orchestrator.createWorldAgent(story.world);
      //   await ctx.db.world.update({
      //     where: { id: story.worldId },
      //     data: { worldAgentId },
      //   });
      // }
      // const agentId = await orchestrator.createStoryAgent(story, story.world);
      // await ctx.db.story.update({
      //   where: { id: input.storyId },
      //   data: { storyAgentId: agentId },
      // });
      // return { agentId };
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
