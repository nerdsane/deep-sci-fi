import { router } from '../trpc';
import { worldRouter } from './worlds';
import { storyRouter } from './stories';
import { authRouter } from './auth';

export const appRouter = router({
  auth: authRouter,
  worlds: worldRouter,
  stories: storyRouter,
});

export type AppRouter = typeof appRouter;
