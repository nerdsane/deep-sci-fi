/**
 * Prisma database client singleton for Next.js
 * Prevents multiple instances in development with hot reloading
 */

import { PrismaClient } from '@prisma/client';

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined;
};

export const db =
  globalForPrisma.prisma ??
  new PrismaClient({
    log: process.env.NODE_ENV === 'development' ? ['query', 'error', 'warn'] : ['error'],
  });

if (process.env.NODE_ENV !== 'production') {
  globalForPrisma.prisma = db;
}

// Helper to check if we're in cloud mode (DATABASE_URL is set)
export function isCloudMode(): boolean {
  return !!process.env.DATABASE_URL;
}
