'use client';

import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { trpc } from '@/lib/trpc';
import { WelcomeSpace } from '@/components/canvas/layout/WelcomeSpace';
import { FeedbackProvider } from '@/components/canvas/context/FeedbackContext';
import '@/app/canvas.css';

export default function WorldsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  // Fetch worlds using tRPC
  const { data: worldsData, isLoading: worldsLoading } = trpc.worlds.list.useQuery(
    undefined,
    { enabled: status === 'authenticated' }
  );

  // Fetch stories using tRPC
  const { data: storiesData, isLoading: storiesLoading } = trpc.stories.list.useQuery(
    {},
    { enabled: status === 'authenticated' }
  );

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin');
    }
  }, [status, router]);

  if (status === 'loading' || worldsLoading || storiesLoading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100vh',
        background: 'var(--bg-primary, #000)',
        color: 'var(--text-primary, #c8c8c8)',
        fontFamily: 'var(--font-mono)',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '2px solid var(--neon-cyan, #00ffcc)',
            borderTopColor: 'transparent',
            borderRadius: '50%',
            margin: '0 auto 1rem',
            animation: 'spin 1s linear infinite',
          }} />
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  const worlds = worldsData?.worlds || [];
  const stories = storiesData || [];

  return (
    <FeedbackProvider>
      <WelcomeSpace
        worlds={worlds}
        stories={stories}
        onSelectWorld={(world) => {
          router.push(`/worlds/${world.id}`);
        }}
        onSelectStory={(story) => {
          router.push(`/worlds/${story.worldId}/stories/${story.id}`);
        }}
        onStartNewWorld={() => {
          router.push('/worlds/new');
        }}
      />
    </FeedbackProvider>
  );
}
