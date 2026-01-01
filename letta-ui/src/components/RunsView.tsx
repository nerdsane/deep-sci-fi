import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import type { Run } from '../types/letta';

interface RunWithDetails extends Run {
  metrics?: any;
  usage?: any;
  steps?: any[];
}

export function RunsView() {
  const [runs, setRuns] = useState<RunWithDetails[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedRun, setExpandedRun] = useState<string | null>(null);
  const [loadingDetails, setLoadingDetails] = useState<string | null>(null);

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

  async function loadRunDetails(runId: string) {
    if (expandedRun === runId) {
      setExpandedRun(null);
      return;
    }

    try {
      setLoadingDetails(runId);
      const [metrics, usage, steps] = await Promise.allSettled([
        api.getRunMetrics(runId),
        api.getRunUsage(runId),
        api.getRunSteps(runId),
      ]);

      setRuns(prevRuns =>
        prevRuns.map(run =>
          run.id === runId
            ? {
                ...run,
                metrics: metrics.status === 'fulfilled' ? metrics.value : null,
                usage: usage.status === 'fulfilled' ? usage.value : null,
                steps: steps.status === 'fulfilled'
                  ? (Array.isArray(steps.value) ? steps.value : steps.value.items || [])
                  : null,
              }
            : run
        )
      );
      setExpandedRun(runId);
    } catch (err) {
      console.error('Failed to load run details:', err);
    } finally {
      setLoadingDetails(null);
    }
  }

  const completedRuns = runs.filter(r => r.status === 'completed').length;
  const failedRuns = runs.filter(r => r.status === 'failed').length;
  const runningRuns = runs.filter(r => r.status === 'running').length;

  if (loading) {
    return <div className="loading">Loading runs...</div>;
  }

  if (error) {
    return (
      <div className="card" style={{ background: 'rgba(255, 0, 255, 0.1)', color: 'var(--magenta)' }}>
        {error}
      </div>
    );
  }

  return (
    <div>
      <div>
        <h2 className="section-title">Runs</h2>
        <p className="section-subtitle">
          Agent execution runs with metrics and usage data
        </p>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value color-teal">{runs.length}</div>
          <div className="stat-label">Total Runs</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-lemon">{runningRuns}</div>
          <div className="stat-label">Running</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-green">{completedRuns}</div>
          <div className="stat-label">Completed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-magenta">{failedRuns}</div>
          <div className="stat-label">Failed</div>
        </div>
      </div>

      <div className="card-list">
        {runs.map((run) => {
          const duration = run.completed_at
            ? (new Date(run.completed_at).getTime() - new Date(run.created_at).getTime()) / 1000
            : null;
          const isExpanded = expandedRun === run.id;
          const isLoading = loadingDetails === run.id;

          return (
            <div key={run.id} className="card" style={{ cursor: 'pointer' }} onClick={() => !isLoading && loadRunDetails(run.id)}>
              <div className="flex justify-between items-start">
                <div style={{ flex: 1 }}>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="font-mono text-small" style={{ color: 'var(--text-primary)' }}>{run.id.slice(0, 16)}...</span>
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
                    Agent: {run.agent_id.slice(0, 12)}...
                  </div>
                </div>
                <div className="text-small text-muted">
                  {new Date(run.created_at).toLocaleString()}
                </div>
              </div>

              {run.stop_reason && (
                <div className="text-small" style={{ marginTop: '0.75rem' }}>
                  <span className="text-muted">Stop reason: </span>
                  <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{run.stop_reason}</span>
                </div>
              )}

              {duration !== null && (
                <div className="text-small" style={{ marginTop: '0.5rem' }}>
                  <span className="text-muted">Duration: </span>
                  <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{duration.toFixed(2)}s</span>
                </div>
              )}

              {isLoading && (
                <div className="text-small text-muted" style={{ marginTop: '1rem' }}>Loading details...</div>
              )}

              {isExpanded && run.usage && (
                <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-subtle)' }}>
                  <div className="text-small text-muted mb-3">Usage</div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
                    {run.usage.completion_tokens && (
                      <div>
                        <div className="text-small text-muted">Completion Tokens</div>
                        <div className="font-mono" style={{ color: 'var(--neon-teal)', fontSize: '1.125rem' }}>
                          {run.usage.completion_tokens.toLocaleString()}
                        </div>
                      </div>
                    )}
                    {run.usage.prompt_tokens && (
                      <div>
                        <div className="text-small text-muted">Prompt Tokens</div>
                        <div className="font-mono" style={{ color: 'var(--neon-green)', fontSize: '1.125rem' }}>
                          {run.usage.prompt_tokens.toLocaleString()}
                        </div>
                      </div>
                    )}
                    {run.usage.total_tokens && (
                      <div>
                        <div className="text-small text-muted">Total Tokens</div>
                        <div className="font-mono" style={{ color: 'var(--neon-lemon)', fontSize: '1.125rem' }}>
                          {run.usage.total_tokens.toLocaleString()}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {isExpanded && run.steps && run.steps.length > 0 && (
                <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-subtle)' }}>
                  <div className="text-small text-muted mb-2">Steps ({run.steps.length})</div>
                  <div style={{ display: 'grid', gap: '0.5rem' }}>
                    {run.steps.slice(0, 5).map((step: any) => (
                      <div key={step.id} style={{
                        padding: '0.75rem',
                        background: 'rgba(0, 255, 136, 0.02)',
                        border: '1px solid var(--border-subtle)',
                        fontSize: '0.75rem',
                      }}>
                        <div className="flex justify-between items-center">
                          <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                            {step.id.slice(0, 12)}...
                          </span>
                          <span className={`badge badge-${step.status === 'completed' ? 'success' : 'neutral'}`}>
                            {step.status}
                          </span>
                        </div>
                      </div>
                    ))}
                    {run.steps.length > 5 && (
                      <div className="text-small text-muted">+ {run.steps.length - 5} more steps</div>
                    )}
                  </div>
                </div>
              )}

              {isExpanded && run.metrics && (
                <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-subtle)' }}>
                  <div className="text-small text-muted mb-2">Metrics</div>
                  <pre style={{
                    background: 'rgba(0, 0, 0, 0.3)',
                    padding: '0.75rem',
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary)',
                    overflow: 'auto',
                    lineHeight: '1.5',
                  }}>
                    {JSON.stringify(run.metrics, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {runs.length === 0 && (
        <div className="empty-state">No runs found</div>
      )}
    </div>
  );
}
