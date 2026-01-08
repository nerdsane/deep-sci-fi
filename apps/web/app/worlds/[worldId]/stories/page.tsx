'use client';

import { useSession } from 'next-auth/react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { trpc } from '@/lib/trpc';
import '../../../worlds/worlds.css';

export default function StoriesPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const params = useParams();
  const worldId = params.worldId as string;

  // Fetch world and stories
  const { data: worldData, isLoading: worldLoading } = trpc.worlds.getById.useQuery(
    { id: worldId },
    { enabled: status === 'authenticated' }
  );

  const { data: storiesData, isLoading: storiesLoading } = trpc.stories.list.useQuery(
    { worldId },
    { enabled: status === 'authenticated' }
  );

  if (status === 'loading' || worldLoading || storiesLoading) {
    return (
      <div className="worlds-page worlds-page--loading">
        <div className="loading-indicator">
          <div className="loading-spinner"></div>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (status === 'unauthenticated') {
    router.push('/auth/signin');
    return null;
  }

  if (!worldData) {
    return (
      <div className="worlds-page">
        <div className="worlds-container">
          <div className="worlds-empty">
            <div className="worlds-empty__icon">⚠️</div>
            <h2 className="worlds-empty__title">World not found</h2>
            <Link href="/worlds" className="worlds-empty__button">
              ← Back to Worlds
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const stories = storiesData?.stories || [];

  return (
    <div className="worlds-page">
      <div className="worlds-container">
        <header className="worlds-header">
          <div className="worlds-header__content">
            <Link href="/worlds" className="worlds-header__breadcrumb">
              ← Worlds
            </Link>
            <h1 className="worlds-header__title">
              <span className="worlds-header__accent">◈</span> {worldData.name}
            </h1>
            <p className="worlds-header__subtitle">Stories in this world</p>
          </div>
          <Link
            href={`/worlds/${worldId}/stories/new`}
            className="worlds-header__button"
          >
            + New Story
          </Link>
        </header>

        {stories.length === 0 ? (
          <div className="worlds-empty">
            <div className="worlds-empty__icon">📖</div>
            <h2 className="worlds-empty__title">No stories yet</h2>
            <p className="worlds-empty__description">
              Create your first story in this world
            </p>
            <Link
              href={`/worlds/${worldId}/stories/new`}
              className="worlds-empty__button"
            >
              Create First Story
            </Link>
          </div>
        ) : (
          <div className="worlds-grid">
            {stories.map((story) => (
              <Link
                key={story.id}
                href={`/worlds/${worldId}/stories/${story.id}`}
                className="world-card"
              >
                <div className="world-card__header">
                  <h3 className="world-card__title">{story.title}</h3>
                  <span className="world-card__badge">
                    {story.storyAgentId ? '✓' : '○'}
                  </span>
                </div>
                <p className="world-card__description">
                  {story.description || 'No description'}
                </p>
                <div className="world-card__footer">
                  <span className="world-card__meta">
                    {story._count?.segments || 0} segments
                  </span>
                  <span className="world-card__meta">
                    {new Date(story.updatedAt).toLocaleDateString()}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
