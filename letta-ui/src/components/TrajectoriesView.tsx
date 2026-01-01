import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import type { Trajectory } from '../types/letta';

export function TrajectoriesView() {
  const [trajectories, setTrajectories] = useState<Trajectory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadTrajectories();
  }, []);

  async function loadTrajectories() {
    try {
      setLoading(true);
      const response = await api.listTrajectories();
      setTrajectories(Array.isArray(response) ? response : response.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load trajectories');
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!searchQuery.trim()) {
      loadTrajectories();
      return;
    }

    try {
      setLoading(true);
      const response = await api.searchTrajectories(searchQuery);
      setTrajectories(response.trajectories || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  const successCount = trajectories.filter((t) => t.data?.outcome?.type === 'success').length;
  const failureCount = trajectories.filter((t) => t.data?.outcome?.type === 'failure').length;

  if (loading && trajectories.length === 0) {
    return <div className="loading">Loading trajectories...</div>;
  }

  return (
    <div>
      <div>
        <h2 className="section-title">Trajectories</h2>
        <p className="section-subtitle">
          Execution traces for continual learning
        </p>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value color-teal">{trajectories.length}</div>
          <div className="stat-label">Total Trajectories</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-green">{successCount}</div>
          <div className="stat-label">Successful</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-magenta">{failureCount}</div>
          <div className="stat-label">Failed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-lemon">
            {successCount + failureCount > 0
              ? Math.round((successCount / (successCount + failureCount)) * 100)
              : 0}
            %
          </div>
          <div className="stat-label">Success Rate</div>
        </div>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="search-form">
        <div className="search-controls">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search trajectories by semantic similarity..."
            className="input"
            style={{ flex: 1 }}
          />
          <button type="submit" className="btn btn-primary">
            Search
          </button>
          {searchQuery && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('');
                loadTrajectories();
              }}
              className="btn btn-secondary"
            >
              Clear
            </button>
          )}
        </div>
      </form>

      {error && (
        <div className="card" style={{ background: 'rgba(255, 0, 255, 0.1)', color: 'var(--magenta)', marginBottom: '1.5rem' }}>
          {error}
        </div>
      )}

      {/* Trajectory list */}
      <div className="card-list">
        {trajectories.map((trajectory) => {
          const outcome = trajectory.data?.outcome;
          const metadata = trajectory.data?.metadata;

          return (
            <div key={trajectory.id} className="card">
              <div className="flex justify-between items-start mb-3">
                <div style={{ flex: 1 }}>
                  <div className="flex items-center gap-3 mb-3">
                    <span
                      className={`badge ${
                        outcome?.type === 'success'
                          ? 'badge-success'
                          : outcome?.type === 'failure'
                          ? 'badge-failure'
                          : 'badge-neutral'
                      }`}
                    >
                      {outcome?.type || 'unknown'}
                    </span>
                    <span className="text-small text-muted font-mono">
                      Score: {trajectory.outcome_score?.toFixed(2) || 'N/A'}
                    </span>
                  </div>
                  {trajectory.summary && (
                    <p style={{ color: 'var(--text-secondary)', lineHeight: '1.7', fontSize: '0.9375rem' }}>{trajectory.summary}</p>
                  )}
                </div>
              </div>

              {metadata && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1.25rem', fontSize: '0.875rem', marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border)' }}>
                  <div>
                    <span className="text-muted">Steps:</span>
                    <span className="font-mono" style={{ marginLeft: '0.5rem', color: 'var(--text-secondary)' }}>{metadata.step_count}</span>
                  </div>
                  <div>
                    <span className="text-muted">Messages:</span>
                    <span className="font-mono" style={{ marginLeft: '0.5rem', color: 'var(--text-secondary)' }}>{metadata.message_count}</span>
                  </div>
                  <div>
                    <span className="text-muted">Tokens:</span>
                    <span className="font-mono" style={{ marginLeft: '0.5rem', color: 'var(--text-secondary)' }}>{metadata.total_tokens}</span>
                  </div>
                  <div>
                    <span className="text-muted">Duration:</span>
                    <span className="font-mono" style={{ marginLeft: '0.5rem', color: 'var(--text-secondary)' }}>
                      {metadata.duration_ns
                        ? `${(metadata.duration_ns / 1_000_000_000).toFixed(1)}s`
                        : 'N/A'}
                    </span>
                  </div>
                </div>
              )}

              <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border)' }} className="flex justify-between items-center text-small">
                <span className="text-muted font-mono">
                  Agent: {trajectory.agent_id.slice(0, 12)}
                </span>
                <span className="text-muted">
                  {new Date(trajectory.created_at).toLocaleString()}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {trajectories.length === 0 && !loading && (
        <div className="empty-state">No trajectories found</div>
      )}
    </div>
  );
}
