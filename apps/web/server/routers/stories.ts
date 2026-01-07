import { router, protectedProcedure } from '../trpc';
import { z } from 'zod';
import { TRPCError } from '@trpc/server';

export const storyRouter = router({
  // List stories (optionally filtered by world)
  list: protectedProcedure
    .input(
      z.object({
        worldId: z.string().optional(),
      })
    )
    .query(async ({ ctx, input }) => {
      const stories = await ctx.db.story.findMany({
        where: {
          ...(input.worldId ? { worldId: input.worldId } : {}),
          OR: [
            { authorId: ctx.session.user.id },
            {
              world: {
                OR: [
                  { ownerId: ctx.session.user.id },
                  {
                    collaborators: {
                      some: { userId: ctx.session.user.id },
                    },
                  },
                ],
              },
            },
          ],
        },
        include: {
          author: {
            select: {
              id: true,
              name: true,
              email: true,
            },
          },
          world: {
            select: {
              id: true,
              name: true,
            },
          },
          _count: {
            select: {
              segments: true,
            },
          },
        },
        orderBy: {
          updatedAt: 'desc',
        },
      });

      return stories;
    }),

  // Get single story
  get: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ ctx, input }) => {
      const story = await ctx.db.story.findUnique({
        where: { id: input.id },
        include: {
          author: {
            select: {
              id: true,
              name: true,
              email: true,
            },
          },
          world: true,
          segments: {
            orderBy: {
              createdAt: 'asc',
            },
          },
        },
      });

      if (!story) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'Story not found',
        });
      }

      // Check access
      const hasAccess =
        story.authorId === ctx.session.user.id ||
        story.world.ownerId === ctx.session.user.id;

      if (!hasAccess) {
        throw new TRPCError({
          code: 'FORBIDDEN',
          message: 'Access denied',
        });
      }

      return story;
    }),

  // Create story
  create: protectedProcedure
    .input(
      z.object({
        worldId: z.string(),
        title: z.string(),
        metadata: z.any().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Check world access
      const world = await ctx.db.world.findUnique({
        where: { id: input.worldId },
      });

      if (!world) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'World not found',
        });
      }

      const story = await ctx.db.story.create({
        data: {
          worldId: input.worldId,
          authorId: ctx.session.user.id,
          title: input.title,
          metadata: input.metadata || {
            status: 'active',
            tags: [],
          },
          worldContributions: {
            characters_developed: [],
            locations_explored: [],
            rules_tested: [],
            new_rules_discovered: [],
            contradictions_found: [],
            themes_explored: [],
          },
        },
      });

      // TODO: Create story agent via Letta Orchestrator

      return story;
    }),
});
