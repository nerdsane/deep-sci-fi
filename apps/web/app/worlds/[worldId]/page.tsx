'use client';

import { useSession } from 'next-auth/react';
import { useRouter, useParams } from 'next/navigation';
import { useEffect } from 'react';
import { trpc } from '@/lib/trpc';
import { WorldSpace } from '@/components/canvas/world/WorldSpace';
import { FeedbackProvider } from '@/components/canvas/context/FeedbackContext';
import '@/app/canvas.css';

export default function WorldPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const params = useParams();
  const worldId = params?.worldId as string;

  // Fetch world data
  const { data: world, isLoading: worldLoading } = trpc.worlds.getById.useQuery(
    { id: worldId },
    { enabled: status === 'authenticated' && !!worldId }
  );

  // Fetch stories in this world
  const { data: stories, isLoading: storiesLoading } = trpc.stories.list.useQuery(
    { worldId },
    { enabled: status === 'authenticated' && !!worldId }
  );

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin');
    }
  }, [status, router]);

  if (status === 'loading' || worldLoading || storiesLoading) {
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
          <p>Loading world...</p>
        </div>
      </div>
    );
  }

  if (!session || !world) {
    return null;
  }

  return (
    <FeedbackProvider>
      <WorldSpace
        world={world as any}
        stories={stories || []}
        onSelectStory={(story) => {
          router.push(`/worlds/${worldId}/stories/${story.id}`);
        }}
        onExploreElement={(elementId, elementType) => {
          console.log('Explore element:', elementId, elementType);
          // TODO: Implement element detail view
        }}
        onStartNewStory={() => {
          router.push(`/worlds/${worldId}/stories/new`);
        }}
      />
    </FeedbackProvider>
  );
}
