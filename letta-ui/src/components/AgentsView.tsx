import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import type { Agent } from '../types/letta';

export function AgentsView() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadAgents();
  }, []);

  async function loadAgents() {
    try {
      setLoading(true);
      const response = await api.listAgents();
      setAgents(Array.isArray(response) ? response : response.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load agents');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return <div className="loading">Loading agents...</div>;
  }

  if (error) {
    return (
      <div className="card" style={{ background: 'var(--error)', color: 'white' }}>
        {error}
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="section-title">Agents</h2>
          <p className="section-subtitle">
            {agents.length} active {agents.length === 1 ? 'agent' : 'agents'}
          </p>
        </div>
      </div>

      <div className="card-grid">
        {agents.map((agent) => (
          <div key={agent.id} className="card" style={{ cursor: 'pointer' }}>
            <div className="flex justify-between items-start mb-3">
              <div style={{ flex: 1 }}>
                <h3 className="font-semibold" style={{ fontSize: '1.125rem', marginBottom: '0.5rem', color: 'var(--text)' }}>
                  {agent.name}
                </h3>
                {agent.description && (
                  <p className="text-muted" style={{ lineHeight: '1.5', marginBottom: '1rem' }}>
                    {agent.description}
                  </p>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div className="flex gap-2 items-center text-small">
                <span className="text-muted" style={{ fontWeight: 500 }}>Model:</span>
                <span className="font-mono" style={{ color: 'var(--text)' }}>{agent.model}</span>
              </div>
              <div className="flex gap-2 items-center text-small">
                <span className="text-muted" style={{ fontWeight: 500 }}>Type:</span>
                <span className="badge badge-neutral">{agent.agent_type}</span>
              </div>
              {agent.tags && agent.tags.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.5rem' }}>
                  {agent.tags.map((tag) => (
                    <span key={tag} className="badge badge-neutral">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-light)' }}>
              <span className="text-small text-muted">
                {new Date(agent.created_at).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  year: 'numeric',
                })}
              </span>
            </div>
          </div>
        ))}
      </div>

      {agents.length === 0 && (
        <div className="empty-state">No agents found</div>
      )}
    </div>
  );
}
