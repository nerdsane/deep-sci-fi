import { z } from 'zod';
import { router, protectedProcedure } from '../trpc';
import { getLettaOrchestrator } from '@deep-sci-fi/letta';

/**
 * Chat router - Two-Tier Message Routing
 *
 * Routes messages to appropriate agent based on context:
 * - If worldId present → route to World Agent
 * - If worldId absent → route to User Agent (orchestrator)
 */
export const chatRouter = router({
  /**
   * Send a message to an agent (with automatic routing)
   *
   * Routing Logic:
   * - No worldId → User Agent (orchestrator) for world creation/navigation
   * - With worldId → World Agent for world management/story writing
   * - With worldId + storyId → World Agent with story context set
   */
  sendMessage: protectedProcedure
    .input(z.object({
      message: z.string(),
      context: z.object({
        worldId: z.string().optional(),
        storyId: z.string().optional(),
      }),
    }))
    .mutation(async ({ ctx, input }) => {
      const orchestrator = getLettaOrchestrator();

      // Verify access if world context is provided
      if (input.context.worldId) {
        const world = await ctx.db.world.findUnique({
          where: { id: input.context.worldId },
        });

        if (!world) {
          throw new Error('World not found');
        }

        // Check ownership or collaboration
        if (world.ownerId !== ctx.session.user.id) {
          const hasAccess = await ctx.db.worldCollaborator.findFirst({
            where: {
              worldId: input.context.worldId,
              userId: ctx.session.user.id,
            },
          });

          if (!hasAccess && world.visibility !== 'public') {
            throw new Error('Unauthorized');
          }
        }
      }

      // Verify story access if story context is provided
      if (input.context.storyId) {
        const story = await ctx.db.story.findUnique({
          where: { id: input.context.storyId },
        });

        if (!story) {
          throw new Error('Story not found');
        }

        // Check ownership
        if (story.authorId !== ctx.session.user.id) {
          throw new Error('Unauthorized');
        }

        // Verify story belongs to the world
        if (input.context.worldId && story.worldId !== input.context.worldId) {
          throw new Error('Story does not belong to this world');
        }
      }

      // TODO: Route message to appropriate agent
      // Currently throws "Not yet implemented" error
      throw new Error(
        'sendMessage: Not yet implemented. ' +
        'Letta SDK integration in progress. ' +
        `Context: ${JSON.stringify(input.context)}`
      );

      // Future implementation:
      // const response = await orchestrator.sendMessage(
      //   ctx.session.user.id,
      //   input.message,
      //   input.context
      // );
      //
      // // Optionally store message in database for persistence
      // // ...
      //
      // return response;
    }),

  /**
   * Stream messages from an agent (for real-time responses)
   *
   * TODO: Implement with tRPC subscriptions or Server-Sent Events
   */
  streamMessages: protectedProcedure
    .input(z.object({
      message: z.string(),
      context: z.object({
        worldId: z.string().optional(),
        storyId: z.string().optional(),
      }),
    }))
    .mutation(async ({ ctx, input }) => {
      // TODO: Implement streaming with Letta SDK
      // Use streamSteps: true in agent.messages.send()
      throw new Error(
        'streamMessages: Not yet implemented. ' +
        'Will use Server-Sent Events or tRPC subscriptions for streaming.'
      );
    }),

  /**
   * Get chat history for a specific context
   */
  getChatHistory: protectedProcedure
    .input(z.object({
      worldId: z.string().optional(),
      storyId: z.string().optional(),
      limit: z.number().default(50),
      offset: z.number().default(0),
    }))
    .query(async ({ ctx, input }) => {
      // TODO: Implement chat history storage in database
      // For now, return empty array
      throw new Error(
        'getChatHistory: Not yet implemented. ' +
        'Need to implement message persistence in database.'
      );

      // Future implementation:
      // const messages = await ctx.db.chatMessage.findMany({
      //   where: {
      //     userId: ctx.session.user.id,
      //     worldId: input.worldId,
      //     storyId: input.storyId,
      //   },
      //   orderBy: { createdAt: 'desc' },
      //   take: input.limit,
      //   skip: input.offset,
      // });
      //
      // return { messages };
    }),

  /**
   * Clear chat history for a context
   */
  clearChatHistory: protectedProcedure
    .input(z.object({
      worldId: z.string().optional(),
      storyId: z.string().optional(),
    }))
    .mutation(async ({ ctx, input }) => {
      // TODO: Implement chat history deletion
      throw new Error(
        'clearChatHistory: Not yet implemented. ' +
        'Need to implement message persistence first.'
      );

      // Future implementation:
      // await ctx.db.chatMessage.deleteMany({
      //   where: {
      //     userId: ctx.session.user.id,
      //     worldId: input.worldId,
      //     storyId: input.storyId,
      //   },
      // });
      //
      // return { success: true };
    }),
});
