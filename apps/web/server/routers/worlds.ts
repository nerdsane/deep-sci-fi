import { router, protectedProcedure } from '../trpc';
import { z } from 'zod';
import { TRPCError } from '@trpc/server';

export const worldRouter = router({
  // List user's worlds
  list: protectedProcedure.query(async ({ ctx }) => {
    const worlds = await ctx.db.world.findMany({
      where: {
        OR: [
          { ownerId: ctx.session.user.id },
          {
            collaborators: {
              some: { userId: ctx.session.user.id },
            },
          },
        ],
      },
      include: {
        owner: {
          select: {
            id: true,
            name: true,
            email: true,
          },
        },
        _count: {
          select: {
            stories: true,
          },
        },
      },
      orderBy: {
        updatedAt: 'desc',
      },
    });

    return worlds;
  }),

  // Get single world
  get: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ ctx, input }) => {
      const world = await ctx.db.world.findUnique({
        where: { id: input.id },
        include: {
          owner: {
            select: {
              id: true,
              name: true,
              email: true,
            },
          },
          collaborators: {
            include: {
              user: {
                select: {
                  id: true,
                  name: true,
                  email: true,
                },
              },
            },
          },
          stories: {
            select: {
              id: true,
              title: true,
              createdAt: true,
            },
          },
        },
      });

      if (!world) {
        throw new TRPCError({
          code: 'NOT_FOUND',
          message: 'World not found',
        });
      }

      // Check access
      const hasAccess =
        world.ownerId === ctx.session.user.id ||
        world.collaborators.some((c) => c.userId === ctx.session.user.id) ||
        world.visibility === 'public';

      if (!hasAccess) {
        throw new TRPCError({
          code: 'FORBIDDEN',
          message: 'Access denied',
        });
      }

      return world;
    }),

  // Create world
  create: protectedProcedure
    .input(
      z.object({
        name: z.string(),
        foundation: z.any(), // Foundation JSON
        surface: z.any().optional(), // Surface JSON
        constraints: z.any().optional(), // Constraints JSON
        visibility: z.enum(['private', 'shared', 'public']).optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const world = await ctx.db.world.create({
        data: {
          name: input.name,
          ownerId: ctx.session.user.id,
          foundation: input.foundation,
          surface: input.surface || { visible_elements: [] },
          constraints: input.constraints || [],
          visibility: input.visibility || 'private',
          state: 'sketch',
        },
      });

      // TODO: Create world agent via Letta Orchestrator

      return world;
    }),

  // Update world
  update: protectedProcedure
    .input(
      z.object({
        id: z.string(),
        name: z.string().optional(),
        foundation: z.any().optional(),
        surface: z.any().optional(),
        constraints: z.any().optional(),
        state: z.enum(['sketch', 'draft', 'detailed']).optional(),
        visibility: z.enum(['private', 'shared', 'public']).optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      // Check ownership
      const world = await ctx.db.world.findUnique({
        where: { id: input.id },
      });

      if (!world || world.ownerId !== ctx.session.user.id) {
        throw new TRPCError({
          code: 'FORBIDDEN',
          message: 'Access denied',
        });
      }

      const updatedWorld = await ctx.db.world.update({
        where: { id: input.id },
        data: {
          name: input.name,
          foundation: input.foundation,
          surface: input.surface,
          constraints: input.constraints,
          state: input.state,
          visibility: input.visibility,
          version: { increment: 1 },
        },
      });

      return updatedWorld;
    }),

  // Delete world
  delete: protectedProcedure
    .input(z.object({ id: z.string() }))
    .mutation(async ({ ctx, input }) => {
      // Check ownership
      const world = await ctx.db.world.findUnique({
        where: { id: input.id },
      });

      if (!world || world.ownerId !== ctx.session.user.id) {
        throw new TRPCError({
          code: 'FORBIDDEN',
          message: 'Access denied',
        });
      }

      await ctx.db.world.delete({
        where: { id: input.id },
      });

      return { success: true };
    }),
});
