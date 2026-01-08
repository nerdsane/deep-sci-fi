import { z } from 'zod';
import { router, protectedProcedure } from '../trpc';
import { getLettaOrchestrator } from '@deep-sci-fi/letta';

/**
 * Agent management router - Two-Tier Architecture
 *
 * User Agent (Orchestrator): ONE per user - handles world creation and routing
 * World Agent: ONE per world - handles world AND all stories in that world
 */
export const agentsRouter = router({
  /**
   * Get or create User Agent (Orchestrator) for the current user
   * This is the equivalent of letta-code's createAgent()
   *
   * Universal API - works for both Web UI and CLI clients
   */
  getUserAgent: protectedProcedure
    .query(async ({ ctx }) => {
      const user = await ctx.db.user.findUnique({
        where: { id: ctx.session.user.id },
      });

      if (!user) {
        throw new Error('User not found');
      }

      const orchestrator = getLettaOrchestrator(ctx.db);
      const userAgentId = await orchestrator.getOrCreateUserAgent(user.id, user);

      return { agentId: userAgentId };
    }),

  /**
   * Get or create World Agent for a specific world
   * World Agent handles BOTH world management AND all stories in the world
   */
  getOrCreateWorldAgent: protectedProcedure
    .input(z.object({
      worldId: z.string(),
    }))
    .mutation(async ({ ctx, input }) => {
      // Get world from database
      const world = await ctx.db.world.findUnique({
        where: { id: input.worldId },
        include: { owner: true },
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

      const orchestrator = getLettaOrchestrator(ctx.db);
      const worldAgentId = await orchestrator.getOrCreateWorldAgent(input.worldId, world, world.owner);

      return { agentId: worldAgentId };
    }),

  /**
   * Set story context in world agent memory
   * Updates the current_story memory block so agent knows which story is active
   */
  setStoryContext: protectedProcedure
    .input(z.object({
      agentId: z.string(),
      storyId: z.string(),
    }))
    .mutation(async ({ ctx, input }) => {
      // Get story to set as context
      const story = await ctx.db.story.findUnique({
        where: { id: input.storyId },
      });

      if (!story) {
        throw new Error('Story not found');
      }

      // Check ownership
      if (story.authorId !== ctx.session.user.id) {
        throw new Error('Unauthorized');
      }

      const orchestrator = getLettaOrchestrator(ctx.db);
      await orchestrator.setStoryContext(input.agentId, story);

      return { success: true };
    }),

  /**
   * Get agent status
   * Check if an agent exists and what it's associated with
   */
  getAgentStatus: protectedProcedure
    .input(z.object({
      agentId: z.string(),
    }))
    .query(async ({ ctx, input }) => {
      // Check if this is a user agent
      const user = await ctx.db.user.findFirst({
        where: { userAgentId: input.agentId },
      });

      if (user) {
        return {
          exists: true,
          type: 'user' as const,
          userId: user.id,
        };
      }

      // Check if this is a world agent
      const world = await ctx.db.world.findFirst({
        where: { worldAgentId: input.agentId },
      });

      if (world) {
        return {
          exists: true,
          type: 'world' as const,
          worldId: world.id,
        };
      }

      // Agent doesn't exist in database
      return {
        exists: false,
      };
    }),
});
