'use client';

import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useEffect } from 'react';
import { trpc } from '@/lib/trpc';
import { ChatPanelContainer } from '@/components/chat/ChatPanelContainer';
import './worlds.css';

export default function WorldsPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  // Fetch worlds using tRPC
  const { data: worldsData, isLoading: worldsLoading } = trpc.worlds.list.useQuery(
    undefined,
    { enabled: status === 'authenticated' }
  );

  useEffect(() => {
    if (status === 'unauthenticated') {
      router.push('/auth/signin');
    }
  }, [status, router]);

  if (status === 'loading' || worldsLoading) {
    return (
      <div className="worlds-page worlds-page--loading">
        <div className="loading-indicator">
          <div className="loading-spinner"></div>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  const worlds = worldsData?.worlds || [];

  return (
    <div className="worlds-page">
      <div className="worlds-container">
        <header className="worlds-header">
          <div className="worlds-header__content">
            <h1 className="worlds-header__title">
              <span className="worlds-header__accent">◈</span> Your Worlds
            </h1>
            <p className="worlds-header__subtitle">
              Manage your sci-fi universes and world-building projects
            </p>
          </div>
          <Link href="/worlds/new" className="worlds-header__button">
            + Create World
          </Link>
        </header>

        {worlds.length === 0 ? (
          <div className="worlds-empty">
            <div className="worlds-empty__icon">🌌</div>
            <h2 className="worlds-empty__title">No worlds yet</h2>
            <p className="worlds-empty__description">
              Create your first sci-fi universe to start building immersive stories
            </p>
            <Link href="/worlds/new" className="worlds-empty__button">
              Create Your First World
            </Link>
          </div>
        ) : (
          <div className="worlds-grid">
            {worlds.map((world) => (
              <Link
                key={world.id}
                href={`/worlds/${world.id}`}
                className="world-card"
              >
                <div className="world-card__header">
                  <h3 className="world-card__title">{world.name}</h3>
                  <span className="world-card__badge">
                    {world.visibility === 'public' ? '🌐' : '🔒'}
                  </span>
                </div>
                <p className="world-card__description">
                  {world.foundation?.summary || 'No description'}
                </p>
                <div className="world-card__footer">
                  <span className="world-card__meta">
                    {world._count?.stories || 0} stories
                  </span>
                  <span className="world-card__meta">
                    {world.worldAgentId ? '✓ Agent' : '○ No agent'}
                  </span>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* User Agent Chat Panel - Active when no world is selected */}
      <ChatPanelContainer
        viewMode="canvas"
        placeholder="Ask me to create a world, or select a world to work on..."
      />
    </div>
  );
}
