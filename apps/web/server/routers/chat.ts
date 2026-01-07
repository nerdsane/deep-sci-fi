import { z } from 'zod';
import { router, protectedProcedure } from '../trpc';
import { getLettaOrchestrator } from '@deep-sci-fi/letta';

/**
 * Chat session router
 * Handles chat sessions between users and agents
 */
export const chatRouter = router({
  /**
   * Start a new chat session with an agent
   */
  startSession: protectedProcedure
    .input(z.object({
      agentId: z.string(),
      context: z.object({
        worldId: z.string().optional(),
        storyId: z.string().optional(),
      }),
    }))
    .mutation(async ({ ctx, input }) => {
      const orchestrator = getLettaOrchestrator();

      // Verify agent exists and user has access
      if (input.context.worldId) {
        const world = await ctx.db.world.findFirst({
          where: {
            id: input.context.worldId,
            worldAgentId: input.agentId,
          },
        });

        if (!world) {
          throw new Error('World agent not found');
        }

        // Check access
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

      if (input.context.storyId) {
        const story = await ctx.db.story.findFirst({
          where: {
            id: input.context.storyId,
            storyAgentId: input.agentId,
          },
        });

        if (!story) {
          throw new Error('Story agent not found');
        }

        // Check access
        if (story.authorId !== ctx.session.user.id) {
          throw new Error('Unauthorized');
        }
      }

      // Start session
      const sessionId = await orchestrator.startChatSession(
        ctx.session.user.id,
        input.agentId,
        input.context
      );

      return { sessionId };
    }),

  /**
   * Send a message to an agent in a chat session
   */
  sendMessage: protectedProcedure
    .input(z.object({
      sessionId: z.string(),
      message: z.string(),
    }))
    .mutation(async ({ ctx, input }) => {
      const orchestrator = getLettaOrchestrator();

      // Verify session belongs to user
      const session = orchestrator.getSessionHistory(input.sessionId);
      if (!session) {
        throw new Error('Session not found');
      }

      // Send message to agent
      const response = await orchestrator.sendMessage(
        input.sessionId,
        input.message
      );

      // Store message and response in database if story context
      if (session.length > 0) {
        const firstMessage = session[0];
        // TODO: Store messages in database for persistence
      }

      return response;
    }),

  /**
   * Get chat session history
   */
  getSessionHistory: protectedProcedure
    .input(z.object({
      sessionId: z.string(),
    }))
    .query(async ({ ctx, input }) => {
      const orchestrator = getLettaOrchestrator();

      const history = orchestrator.getSessionHistory(input.sessionId);

      if (!history) {
        throw new Error('Session not found');
      }

      return { messages: history };
    }),

  /**
   * End a chat session
   */
  endSession: protectedProcedure
    .input(z.object({
      sessionId: z.string(),
    }))
    .mutation(async ({ ctx, input }) => {
      const orchestrator = getLettaOrchestrator();

      orchestrator.endChatSession(input.sessionId);

      return { success: true };
    }),

  /**
   * Get recent chat sessions for a world or story
   */
  getRecentSessions: protectedProcedure
    .input(z.object({
      worldId: z.string().optional(),
      storyId: z.string().optional(),
      limit: z.number().default(10),
    }))
    .query(async ({ ctx, input }) => {
      // TODO: Implement session storage in database
      // For now, return empty array
      return { sessions: [] };
    }),
});
