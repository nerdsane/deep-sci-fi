import { router, publicProcedure, protectedProcedure } from '../trpc';
import { z } from 'zod';
import bcrypt from 'bcrypt';
import { TRPCError } from '@trpc/server';

export const authRouter = router({
  // Sign up with email/password
  signUp: publicProcedure
    .input(
      z.object({
        email: z.string().email(),
        password: z.string().min(8),
        name: z.string().optional(),
      })
    )
    .mutation(async ({ ctx, input }) => {
      const existingUser = await ctx.db.user.findUnique({
        where: { email: input.email },
      });

      if (existingUser) {
        throw new TRPCError({
          code: 'CONFLICT',
          message: 'User already exists',
        });
      }

      const hashedPassword = await bcrypt.hash(input.password, 10);

      const user = await ctx.db.user.create({
        data: {
          email: input.email,
          password: hashedPassword,
          name: input.name,
          provider: 'email',
        },
      });

      return {
        id: user.id,
        email: user.email,
        name: user.name,
      };
    }),

  // Get current user
  me: protectedProcedure.query(async ({ ctx }) => {
    const user = await ctx.db.user.findUnique({
      where: { id: ctx.session.user.id },
      select: {
        id: true,
        email: true,
        name: true,
        image: true,
        createdAt: true,
      },
    });

    return user;
  }),
});
