import { usePathname, useParams } from 'next/navigation';
import { useMemo } from 'react';

/**
 * Navigation context derived from URL
 */
export interface NavigationContext {
  type: 'worlds-list' | 'world' | 'story' | 'unknown';
  worldId: string | null;
  storyId: string | null;
}

/**
 * Derive navigation context from current URL
 *
 * This hook analyzes the current route and extracts:
 * - Context type (worlds-list, world, story)
 * - World ID (if in world or story)
 * - Story ID (if in story)
 *
 * Used to determine which agent should be active:
 * - worlds-list → User Agent
 * - world → World Agent (for that world)
 * - story → World Agent (for that world, with story context set)
 */
export function useNavigationContext(): NavigationContext {
  const pathname = usePathname();
  const params = useParams();

  const context = useMemo(() => {
    // Worlds list page: /worlds
    if (pathname === '/worlds') {
      return {
        type: 'worlds-list' as const,
        worldId: null,
        storyId: null,
      };
    }

    // Story page: /worlds/[worldId]/stories/[storyId]
    if (pathname.match(/^\/worlds\/[^/]+\/stories\/[^/]+$/)) {
      return {
        type: 'story' as const,
        worldId: (params.worldId as string) || null,
        storyId: (params.storyId as string) || null,
      };
    }

    // World detail page: /worlds/[worldId]
    if (pathname.match(/^\/worlds\/[^/]+$/)) {
      return {
        type: 'world' as const,
        worldId: (params.worldId as string) || null,
        storyId: null,
      };
    }

    // Unknown/other page
    return {
      type: 'unknown' as const,
      worldId: null,
      storyId: null,
    };
  }, [pathname, params]);

  return context;
}
