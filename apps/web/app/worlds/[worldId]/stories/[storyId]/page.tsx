'use client';

import { useSession } from 'next-auth/react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useEffect } from 'react';
import { trpc } from '@/lib/trpc';
import { VisualNovelReader } from '@/components/story/VisualNovelReader';
import './story.css';

export default function StoryPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const params = useParams();
  const worldId = params?.worldId as string;
  const storyId = params?.storyId as string;

  // Fetch story with segments
  const { data: story, isLoading: storyLoading } = trpc.stories.getById.useQuery(
    { id: storyId },
    { enabled: status === 'authenticated' && !!storyId }
  );

  // Fetch world data
  const { data: world, isLoading: worldLoading } = trpc.worlds.getById.useQuery(
    { id: worldId },
    { enabled: status === 'authenticated' && !!worldId }
  );

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin');
    }
  }, [status, router]);

  // Verify story belongs to world
  useEffect(() => {
    if (story && story.worldId !== worldId) {
      router.push(`/worlds/${worldId}`);
    }
  }, [story, worldId, router]);

  if (status === 'loading' || storyLoading || worldLoading) {
    return (
      <div className="story-page story-page--loading">
        <div className="loading-indicator">
          <div className="loading-spinner"></div>
          <p>Loading story...</p>
        </div>
      </div>
    );
  }

  if (!session || !story || !world) {
    return null;
  }

  return (
    <div className="story-page">
      {/* Story Reader */}
      <div className="story-reader">
        {/* Header */}
        <header className="story-header">
          <Link href={`/worlds/${worldId}`} className="story-header__back">
            ← Back to {world.name}
          </Link>
          <div className="story-header__content">
            <h1 className="story-header__title">{story.title}</h1>
            {story.description && (
              <p className="story-header__subtitle">{story.description}</p>
            )}
          </div>
          <div className="story-header__meta">
            <span className="story-header__badge">
              {story.status === 'draft' ? '📝 Draft' : '✓ Published'}
            </span>
            <span className="story-header__badge">
              {story.segments?.length || 0} segments
            </span>
          </div>
        </header>

        {/* Visual Novel Reader */}
        <div className="story-content">
          {story.segments && story.segments.length > 0 ? (
            <VisualNovelReader segments={story.segments} />
          ) : (
            <div className="story-empty">
              <div className="story-empty__icon">✨</div>
              <h2 className="story-empty__title">Story just beginning</h2>
              <p className="story-empty__description">
                Use the chat panel to start writing the first segment of your story.
                The agent will help you craft an immersive narrative.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
