import { router } from '../trpc';
import { worldRouter } from './worlds';
import { storyRouter } from './stories';
import { authRouter } from './auth';
import { agentsRouter } from './agents';
import { chatRouter } from './chat';

export const appRouter = router({
  auth: authRouter,
  worlds: worldRouter,
  stories: storyRouter,
  agents: agentsRouter,
  chat: chatRouter,
});

export type AppRouter = typeof appRouter;
