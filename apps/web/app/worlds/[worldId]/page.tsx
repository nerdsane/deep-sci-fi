'use client';

import { useSession } from 'next-auth/react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { useEffect } from 'react';
import { trpc } from '@/lib/trpc';
import { ChatPanelContainer } from '@/components/chat/ChatPanelContainer';
import './world.css';

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
  const { data: storiesData, isLoading: storiesLoading } = trpc.stories.list.useQuery(
    { worldId },
    { enabled: status === 'authenticated' && !!worldId }
  );

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin');
    }
  }, [status, router]);

  if (status === 'loading' || worldLoading) {
    return (
      <div className="world-page world-page--loading">
        <div className="loading-indicator">
          <div className="loading-spinner"></div>
          <p>Loading world...</p>
        </div>
      </div>
    );
  }

  if (!session || !world) {
    return null;
  }

  const stories = storiesData?.stories || [];
  const foundation = world.foundation as any;

  return (
    <div className="world-page">
      <div className="world-container">
        {/* Header */}
        <header className="world-header">
          <Link href="/worlds" className="world-header__back">
            ← Back to Worlds
          </Link>
          <div className="world-header__content">
            <h1 className="world-header__title">{world.name}</h1>
            <p className="world-header__subtitle">
              {foundation?.summary || world.description || 'No description'}
            </p>
          </div>
          <div className="world-header__meta">
            <span className="world-header__badge">
              {world.visibility === 'public' ? '🌐 Public' : '🔒 Private'}
            </span>
            <span className="world-header__badge">
              {world.worldAgentId ? '✓ Agent Active' : '○ No Agent'}
            </span>
          </div>
        </header>

        {/* World Foundation */}
        {foundation && (
          <section className="world-section">
            <h2 className="world-section__title">World Foundation</h2>
            <div className="world-foundation">
              {foundation.premise && (
                <div className="foundation-card">
                  <h3 className="foundation-card__title">Premise</h3>
                  <p className="foundation-card__content">{foundation.premise}</p>
                </div>
              )}
              {foundation.technology && (
                <div className="foundation-card">
                  <h3 className="foundation-card__title">Technology</h3>
                  <p className="foundation-card__content">{foundation.technology}</p>
                </div>
              )}
              {foundation.society && (
                <div className="foundation-card">
                  <h3 className="foundation-card__title">Society</h3>
                  <p className="foundation-card__content">{foundation.society}</p>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Stories Section */}
        <section className="world-section">
          <div className="world-section__header">
            <h2 className="world-section__title">Stories</h2>
            <Link
              href={`/worlds/${worldId}/stories/new`}
              className="world-section__button"
            >
              + New Story
            </Link>
          </div>

          {storiesLoading ? (
            <div className="loading-indicator">
              <div className="loading-spinner"></div>
              <p>Loading stories...</p>
            </div>
          ) : stories.length === 0 ? (
            <div className="stories-empty">
              <div className="stories-empty__icon">📖</div>
              <h3 className="stories-empty__title">No stories yet</h3>
              <p className="stories-empty__description">
                Start writing your first story in this world
              </p>
              <Link
                href={`/worlds/${worldId}/stories/new`}
                className="stories-empty__button"
              >
                Create First Story
              </Link>
            </div>
          ) : (
            <div className="stories-grid">
              {stories.map((story) => (
                <Link
                  key={story.id}
                  href={`/worlds/${worldId}/stories/${story.id}`}
                  className="story-card"
                >
                  <div className="story-card__header">
                    <h3 className="story-card__title">{story.title}</h3>
                    <span className="story-card__status">
                      {story.status === 'draft' ? '📝' : '✓'}
                    </span>
                  </div>
                  {story.description && (
                    <p className="story-card__description">{story.description}</p>
                  )}
                  <div className="story-card__footer">
                    <span className="story-card__meta">
                      {story._count?.segments || 0} segments
                    </span>
                    <span className="story-card__meta">
                      Updated {new Date(story.updatedAt).toLocaleDateString()}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </div>

      {/* World Agent Chat Panel */}
      <ChatPanelContainer
        worldId={worldId}
        viewMode="canvas"
        placeholder="Ask me about this world or create a story..."
      />
    </div>
  );
}
