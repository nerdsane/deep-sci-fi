'use client';

import { useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import { trpc } from '@/lib/trpc';
import '../../../../worlds/worlds.css';
import '../../../../worlds/new/new-world.css';

export default function NewStoryPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const params = useParams();
  const worldId = params.worldId as string;

  const { data: worldData } = trpc.worlds.getById.useQuery(
    { id: worldId },
    { enabled: status === 'authenticated' }
  );
  const createStoryMutation = trpc.stories.create.useMutation();

  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (status === 'loading') {
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
    router.push('/auth/signin');
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      await createStoryMutation.mutateAsync({
        title,
        description,
        worldId,
      });

      router.push(`/worlds/${worldId}/stories`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create story');
      setLoading(false);
    }
  };

  return (
    <div className="worlds-page">
      <div className="worlds-container">
        <header className="worlds-header">
          <div className="worlds-header__content">
            <Link href={`/worlds/${worldId}/stories`} className="worlds-header__breadcrumb">
              ← Back to {worldData?.name || 'World'}
            </Link>
            <h1 className="worlds-header__title">
              <span className="worlds-header__accent">◈</span> New Story
            </h1>
            <p className="worlds-header__subtitle">
              Create a new story in {worldData?.name}
            </p>
          </div>
        </header>

        <form className="new-world-form" onSubmit={handleSubmit}>
          {error && (
            <div className="form-error">
              <span className="form-error__icon">⚠</span>
              {error}
            </div>
          )}

          <div className="form-section">
            <h2 className="form-section__title">Story Details</h2>

            <div className="form-field">
              <label htmlFor="title" className="form-label">
                Story Title
              </label>
              <input
                id="title"
                type="text"
                className="form-input"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="The Chronicles of the Nexus"
                required
                disabled={loading}
              />
            </div>

            <div className="form-field">
              <label htmlFor="description" className="form-label">
                Description
              </label>
              <textarea
                id="description"
                className="form-textarea"
                rows={5}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="A brief description of your story..."
                disabled={loading}
              />
              <p className="auth-hint">
                This helps you remember what the story is about
              </p>
            </div>
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="form-button form-button--secondary"
              onClick={() => router.push(`/worlds/${worldId}/stories`)}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="form-button form-button--primary"
              disabled={loading || !title.trim()}
            >
              {loading ? 'Creating...' : 'Create Story'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
