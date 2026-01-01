import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import type { Run } from '../types/letta';

export function RunsView() {
  const [runs, setRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadRuns();
  }, []);

  async function loadRuns() {
    try {
      setLoading(true);
      const response = await api.listRuns();
      setRuns(Array.isArray(response) ? response : response.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load runs');
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return <div className="loading">Loading runs...</div>;
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
      <div>
        <h2 className="section-title">Runs</h2>
        <p className="section-subtitle">
          {runs.length} execution {runs.length === 1 ? 'run' : 'runs'}
        </p>
      </div>

      <div className="card-list">
        {runs.map((run) => (
          <div key={run.id} className="card">
            <div className="flex justify-between items-start">
              <div style={{ flex: 1 }}>
                <div className="flex items-center gap-3 mb-2">
                  <span className="font-mono text-small" style={{ color: 'var(--text)' }}>{run.id}</span>
                  <span
                    className={`badge ${
                      run.status === 'completed'
                        ? 'badge-success'
                        : run.status === 'failed'
                        ? 'badge-failure'
                        : run.status === 'running'
                        ? 'badge-running'
                        : 'badge-neutral'
                    }`}
                  >
                    {run.status}
                  </span>
                </div>
                <div className="text-small text-muted font-mono">
                  Agent: {run.agent_id.slice(0, 8)}...
                </div>
              </div>
              <div className="text-small text-muted">
                {new Date(run.created_at).toLocaleString()}
              </div>
            </div>

            {run.stop_reason && (
              <div className="text-small mt-2">
                <span className="text-muted">Stop reason: </span>
                <span className="font-mono" style={{ color: 'var(--text)' }}>{run.stop_reason}</span>
              </div>
            )}

            {run.completed_at && (
              <div className="text-small mt-2">
                <span className="text-muted">Duration: </span>
                <span className="font-mono" style={{ color: 'var(--text)' }}>
                  {(
                    (new Date(run.completed_at).getTime() - new Date(run.created_at).getTime()) /
                    1000
                  ).toFixed(1)}
                  s
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      {runs.length === 0 && (
        <div className="empty-state">No runs found</div>
      )}
    </div>
  );
}
