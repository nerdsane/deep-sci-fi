import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { db } from '@deep-sci-fi/db';

export async function createContext() {
  const session = await getServerSession(authOptions);

  return {
    session,
    db,
  };
}

export type Context = Awaited<ReturnType<typeof createContext>>;
