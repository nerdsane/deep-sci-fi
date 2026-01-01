import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';

interface Job {
  id: string;
  status: string;
  job_type?: string;
  metadata?: any;
  created_at: string;
  completed_at?: string;
  error?: string;
}

export function JobsView() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [activeJobs, setActiveJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showActive, setShowActive] = useState(false);

  useEffect(() => {
    loadJobs();
  }, [showActive]);

  async function loadJobs() {
    try {
      setLoading(true);
      if (showActive) {
        const response = await api.getActiveJobs();
        setActiveJobs(Array.isArray(response) ? response : response.items || []);
      } else {
        const response = await api.listJobs();
        setJobs(Array.isArray(response) ? response : response.items || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load jobs');
    } finally {
      setLoading(false);
    }
  }

  const displayJobs = showActive ? activeJobs : jobs;
  const completedJobs = jobs.filter(j => j.status === 'completed').length;
  const failedJobs = jobs.filter(j => j.status === 'failed').length;
  const runningJobs = jobs.filter(j => j.status === 'running' || j.status === 'pending').length;

  if (loading) {
    return <div className="loading">Loading jobs...</div>;
  }

  return (
    <div>
      <div>
        <h2 className="section-title">Jobs</h2>
        <p className="section-subtitle">
          Background tasks and async operations
        </p>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value color-teal">{jobs.length}</div>
          <div className="stat-label">Total Jobs</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-lemon">{runningJobs}</div>
          <div className="stat-label">Running</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-green">{completedJobs}</div>
          <div className="stat-label">Completed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-magenta">{failedJobs}</div>
          <div className="stat-label">Failed</div>
        </div>
      </div>

      {/* Filter toggle */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', gap: '0.5rem' }}>
        <button
          onClick={() => setShowActive(false)}
          className={`btn ${!showActive ? 'btn-primary' : 'btn-secondary'}`}
        >
          All Jobs
        </button>
        <button
          onClick={() => setShowActive(true)}
          className={`btn ${showActive ? 'btn-primary' : 'btn-secondary'}`}
        >
          Active Only
        </button>
      </div>

      {error && (
        <div className="card" style={{ background: 'rgba(255, 0, 255, 0.1)', color: 'var(--magenta)', marginBottom: '1.5rem' }}>
          {error}
        </div>
      )}

      {/* Job list */}
      <div className="card-list">
        {displayJobs.map((job) => {
          const duration = job.completed_at
            ? (new Date(job.completed_at).getTime() - new Date(job.created_at).getTime()) / 1000
            : null;

          return (
            <div key={job.id} className="card">
              <div className="flex justify-between items-start">
                <div style={{ flex: 1 }}>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="font-mono text-small" style={{ color: 'var(--text-primary)' }}>
                      {job.id.slice(0, 16)}...
                    </span>
                    <span
                      className={`badge ${
                        job.status === 'completed'
                          ? 'badge-success'
                          : job.status === 'failed'
                          ? 'badge-failure'
                          : job.status === 'running' || job.status === 'pending'
                          ? 'badge-running'
                          : 'badge-neutral'
                      }`}
                    >
                      {job.status}
                    </span>
                    {job.job_type && (
                      <span className="badge badge-neutral text-small">{job.job_type}</span>
                    )}
                  </div>

                  {job.error && (
                    <div style={{
                      marginTop: '0.75rem',
                      padding: '0.75rem',
                      background: 'rgba(255, 0, 255, 0.05)',
                      border: '1px solid rgba(255, 0, 255, 0.2)',
                      color: 'var(--neon-magenta)',
                      fontSize: '0.875rem',
                    }}>
                      Error: {job.error}
                    </div>
                  )}

                  {job.metadata && Object.keys(job.metadata).length > 0 && (
                    <div style={{
                      marginTop: '0.75rem',
                      padding: '0.75rem',
                      background: 'rgba(0, 255, 136, 0.03)',
                      border: '1px solid var(--border-subtle)',
                    }}>
                      <div className="text-small text-muted mb-2">Metadata</div>
                      <pre style={{
                        fontSize: '0.75rem',
                        color: 'var(--text-secondary)',
                        overflow: 'auto',
                        lineHeight: '1.5',
                      }}>
                        {JSON.stringify(job.metadata, null, 2)}
                      </pre>
                    </div>
                  )}

                  <div style={{ marginTop: '0.75rem', display: 'flex', gap: '1.5rem', fontSize: '0.875rem' }}>
                    {duration !== null && (
                      <div className="text-small text-muted">
                        Duration: <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{duration.toFixed(2)}s</span>
                      </div>
                    )}
                  </div>
                </div>
                <div className="text-small text-muted">
                  {new Date(job.created_at).toLocaleString()}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {displayJobs.length === 0 && !loading && (
        <div className="empty-state">No jobs found</div>
      )}
    </div>
  );
}
