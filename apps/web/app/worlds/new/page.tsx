'use client';

import { useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import '../worlds.css';
import './new-world.css';

export default function NewWorldPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const [name, setName] = useState('');
  const [summary, setSummary] = useState('');
  const [visibility, setVisibility] = useState<'private' | 'public'>('private');
  const [foundation, setFoundation] = useState({
    physics: '',
    technology: '',
    society: '',
    history: '',
  });
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
      // TODO: Create world via tRPC
      console.log('Creating world:', { name, summary, visibility, foundation });

      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));

      router.push('/worlds');
    } catch (err) {
      setError('Failed to create world');
      setLoading(false);
    }
  };

  return (
    <div className="worlds-page">
      <div className="worlds-container">
        <header className="worlds-header">
          <div className="worlds-header__content">
            <h1 className="worlds-header__title">
              <span className="worlds-header__accent">◈</span> Create New World
            </h1>
            <p className="worlds-header__subtitle">
              Define the foundation of your sci-fi universe
            </p>
          </div>
          <Link href="/worlds" className="worlds-header__button worlds-header__button--secondary">
            ← Back
          </Link>
        </header>

        <form className="new-world-form" onSubmit={handleSubmit}>
          {error && (
            <div className="form-error">
              <span className="form-error__icon">⚠</span>
              {error}
            </div>
          )}

          <div className="form-section">
            <h2 className="form-section__title">Basic Information</h2>

            <div className="form-field">
              <label htmlFor="name" className="form-label">
                World Name
              </label>
              <input
                id="name"
                type="text"
                className="form-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="The Nexus Expanse"
                required
                disabled={loading}
              />
            </div>

            <div className="form-field">
              <label htmlFor="summary" className="form-label">
                Summary
              </label>
              <textarea
                id="summary"
                className="form-textarea"
                rows={3}
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                placeholder="A brief overview of your world..."
                disabled={loading}
              />
            </div>

            <div className="form-field">
              <label className="form-label">Visibility</label>
              <div className="form-radio-group">
                <label className="form-radio">
                  <input
                    type="radio"
                    name="visibility"
                    value="private"
                    checked={visibility === 'private'}
                    onChange={(e) => setVisibility('private')}
                    disabled={loading}
                  />
                  <span className="form-radio__label">
                    <span className="form-radio__icon">🔒</span>
                    Private
                  </span>
                  <span className="form-radio__description">
                    Only you and collaborators can access
                  </span>
                </label>
                <label className="form-radio">
                  <input
                    type="radio"
                    name="visibility"
                    value="public"
                    checked={visibility === 'public'}
                    onChange={(e) => setVisibility('public')}
                    disabled={loading}
                  />
                  <span className="form-radio__label">
                    <span className="form-radio__icon">🌐</span>
                    Public
                  </span>
                  <span className="form-radio__description">
                    Anyone can view (read-only)
                  </span>
                </label>
              </div>
            </div>
          </div>

          <div className="form-section">
            <h2 className="form-section__title">World Foundation</h2>
            <p className="form-section__description">
              Define the core rules and principles of your universe. These establish
              the fundamental logic that all stories must follow.
            </p>

            <div className="form-field">
              <label htmlFor="physics" className="form-label">
                Physics & Natural Laws
              </label>
              <textarea
                id="physics"
                className="form-textarea"
                rows={4}
                value={foundation.physics}
                onChange={(e) =>
                  setFoundation({ ...foundation, physics: e.target.value })
                }
                placeholder="How does physics work? FTL travel? Gravity manipulation? Energy sources?"
                disabled={loading}
              />
            </div>

            <div className="form-field">
              <label htmlFor="technology" className="form-label">
                Technology Level
              </label>
              <textarea
                id="technology"
                className="form-textarea"
                rows={4}
                value={foundation.technology}
                onChange={(e) =>
                  setFoundation({ ...foundation, technology: e.target.value })
                }
                placeholder="What technologies exist? AI? Cybernetics? Nanotech? What are the limits?"
                disabled={loading}
              />
            </div>

            <div className="form-field">
              <label htmlFor="society" className="form-label">
                Society & Culture
              </label>
              <textarea
                id="society"
                className="form-textarea"
                rows={4}
                value={foundation.society}
                onChange={(e) =>
                  setFoundation({ ...foundation, society: e.target.value })
                }
                placeholder="How is society structured? Government? Economics? Social norms?"
                disabled={loading}
              />
            </div>

            <div className="form-field">
              <label htmlFor="history" className="form-label">
                History & Timeline
              </label>
              <textarea
                id="history"
                className="form-textarea"
                rows={4}
                value={foundation.history}
                onChange={(e) =>
                  setFoundation({ ...foundation, history: e.target.value })
                }
                placeholder="Major historical events? Timeline? How did this world come to be?"
                disabled={loading}
              />
            </div>
          </div>

          <div className="form-actions">
            <button
              type="button"
              className="form-button form-button--secondary"
              onClick={() => router.push('/worlds')}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="form-button form-button--primary"
              disabled={loading || !name.trim()}
            >
              {loading ? 'Creating...' : 'Create World'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
