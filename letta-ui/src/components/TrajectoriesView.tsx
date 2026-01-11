import React, { useEffect, useState } from 'react';
import * as Tabs from '@radix-ui/react-tabs';
import { api } from '../lib/api';
import type { Trajectory } from '../types/letta';
import { StatsSkeleton, TrajectoryListSkeleton, TrajectoryDetailSkeleton } from './LoadingSkeletons';
import { AnalyticsView } from './AnalyticsView';

interface Filters {
  agentId: string;
  outcomeType: string;
  minScore: string;
  maxScore: string;
  startDate: string;
  endDate: string;
  domainType: string;
  includeCrossOrg: boolean;
}

export function TrajectoriesView() {
  const [viewTab, setViewTab] = useState('list');
  const [trajectories, setTrajectories] = useState<Trajectory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedTrajectory, setSelectedTrajectory] = useState<string | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [filters, setFilters] = useState<Filters>({
    agentId: '',
    outcomeType: '',
    minScore: '',
    maxScore: '',
    startDate: '',
    endDate: '',
    domainType: '',
    includeCrossOrg: false,
  });
  const [showFilters, setShowFilters] = useState(false);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);

  // Auto-refresh every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      if (!loading && !searchQuery) {
        loadTrajectories(true); // silent reload
      }
    }, 10000);
    return () => clearInterval(interval);
  }, [loading, searchQuery]);

  useEffect(() => {
    loadTrajectories();
  }, [page]);

  async function loadTrajectories(silent = false) {
    try {
      if (!silent) setLoading(true);
      const response = await api.listTrajectories({ limit: pageSize });
      setTrajectories(Array.isArray(response) ? response : response.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load trajectories');
    } finally {
      if (!silent) setLoading(false);
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
      const minScore = filters.minScore ? parseFloat(filters.minScore) : undefined;
      const response = await api.searchTrajectories(
        searchQuery,
        minScore,
        pageSize,
        filters.domainType || undefined,
        filters.includeCrossOrg
      );
      // Handle both array and object response formats
      const results = response.results || response.trajectories || [];
      setTrajectories(results.map((r: any) => r.trajectory || r));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  async function selectTrajectory(trajectoryId: string) {
    if (selectedTrajectory === trajectoryId) {
      setSelectedTrajectory(null);
      return;
    }

    try {
      setLoadingDetail(true);
      const details = await api.getTrajectory(trajectoryId);
      // Update the trajectory in the list with full details
      setTrajectories(prev =>
        prev.map(t => (t.id === trajectoryId ? { ...t, ...details } : t))
      );
      setSelectedTrajectory(trajectoryId);
    } catch (err) {
      console.error('Failed to load trajectory details:', err);
      setError('Failed to load trajectory details');
    } finally {
      setLoadingDetail(false);
    }
  }

  function applyFilters() {
    const filtered = trajectories.filter(t => {
      if (filters.outcomeType) {
        const status = t.data?.outcome?.execution?.status || t.data?.outcome?.type;
        if (status !== filters.outcomeType) return false;
      }
      if (filters.minScore && (t.outcome_score ?? 0) < parseFloat(filters.minScore)) return false;
      if (filters.maxScore && (t.outcome_score ?? 1) > parseFloat(filters.maxScore)) return false;
      if (filters.startDate && new Date(t.created_at) < new Date(filters.startDate)) return false;
      if (filters.endDate && new Date(t.created_at) > new Date(filters.endDate)) return false;
      return true;
    });
    return filtered;
  }

  const filteredTrajectories = applyFilters();
  const successCount = trajectories.filter((t) => {
    const status = t.data?.outcome?.execution?.status || t.data?.outcome?.type;
    return status === 'completed' || status === 'success';
  }).length;
  const failureCount = trajectories.filter((t) => {
    const status = t.data?.outcome?.execution?.status || t.data?.outcome?.type;
    return status === 'failed' || status === 'failure';
  }).length;

  return (
    <div>
      <div>
        <h2 className="section-title">Trajectories</h2>
        <p className="section-subtitle">
          Execution traces for continual learning
        </p>
      </div>

      <Tabs.Root value={viewTab} onValueChange={setViewTab}>
        <Tabs.List style={{
          display: 'flex',
          gap: '0.5rem',
          marginBottom: '1.5rem',
          borderBottom: '1px solid var(--border-subtle)',
        }}>
          <Tabs.Trigger
            value="list"
            style={{
              padding: '0.75rem 1.5rem',
              background: 'transparent',
              border: 'none',
              color: viewTab === 'list' ? 'var(--neon-teal)' : 'var(--text-muted)',
              borderBottom: viewTab === 'list' ? '2px solid var(--neon-teal)' : '2px solid transparent',
              cursor: 'pointer',
              fontSize: '0.95rem',
              fontWeight: 500,
              transition: 'all 0.2s',
            }}
          >
            List View
          </Tabs.Trigger>
          <Tabs.Trigger
            value="analytics"
            style={{
              padding: '0.75rem 1.5rem',
              background: 'transparent',
              border: 'none',
              color: viewTab === 'analytics' ? 'var(--neon-teal)' : 'var(--text-muted)',
              borderBottom: viewTab === 'analytics' ? '2px solid var(--neon-teal)' : '2px solid transparent',
              cursor: 'pointer',
              fontSize: '0.95rem',
              fontWeight: 500,
              transition: 'all 0.2s',
            }}
          >
            Analytics
          </Tabs.Trigger>
        </Tabs.List>

        <Tabs.Content value="list">
          <div>

      {/* Stats */}
      {loading && trajectories.length === 0 ? (
        <StatsSkeleton />
      ) : (
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
      )}

      {/* Search and Filters */}
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
          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            className="btn btn-secondary"
          >
            {showFilters ? 'Hide Filters' : 'Show Filters'}
          </button>
        </div>

        {/* Advanced Filters */}
        {showFilters && (
          <div style={{
            marginTop: '1rem',
            padding: '1.5rem',
            background: 'rgba(255, 255, 255, 0.02)',
            border: '1px solid var(--border-subtle)',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '1rem',
          }}>
            <div>
              <label className="text-small text-muted mb-1" style={{ display: 'block' }}>
                Agent ID
              </label>
              <input
                type="text"
                value={filters.agentId}
                onChange={(e) => setFilters({ ...filters, agentId: e.target.value })}
                placeholder="Filter by agent..."
                className="input"
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label className="text-small text-muted mb-1" style={{ display: 'block' }}>
                Outcome Type
              </label>
              <select
                value={filters.outcomeType}
                onChange={(e) => setFilters({ ...filters, outcomeType: e.target.value })}
                className="input"
                style={{ width: '100%' }}
              >
                <option value="">All</option>
                <option value="success">Success</option>
                <option value="failure">Failure</option>
                <option value="partial_success">Partial Success</option>
              </select>
            </div>
            <div>
              <label className="text-small text-muted mb-1" style={{ display: 'block' }}>
                Min Score
              </label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.1"
                value={filters.minScore}
                onChange={(e) => setFilters({ ...filters, minScore: e.target.value })}
                placeholder="0.0"
                className="input"
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label className="text-small text-muted mb-1" style={{ display: 'block' }}>
                Max Score
              </label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.1"
                value={filters.maxScore}
                onChange={(e) => setFilters({ ...filters, maxScore: e.target.value })}
                placeholder="1.0"
                className="input"
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label className="text-small text-muted mb-1" style={{ display: 'block' }}>
                Start Date
              </label>
              <input
                type="date"
                value={filters.startDate}
                onChange={(e) => setFilters({ ...filters, startDate: e.target.value })}
                className="input"
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label className="text-small text-muted mb-1" style={{ display: 'block' }}>
                End Date
              </label>
              <input
                type="date"
                value={filters.endDate}
                onChange={(e) => setFilters({ ...filters, endDate: e.target.value })}
                className="input"
                style={{ width: '100%' }}
              />
            </div>
            <div>
              <label className="text-small text-muted mb-1" style={{ display: 'block' }}>
                Domain Type
              </label>
              <select
                value={filters.domainType}
                onChange={(e) => setFilters({ ...filters, domainType: e.target.value })}
                className="input"
                style={{ width: '100%' }}
              >
                <option value="">All domains</option>
                <option value="story_agent">Story Agent</option>
                <option value="code_agent">Code Agent</option>
                <option value="research_agent">Research Agent</option>
                <option value="chat_agent">Chat Agent</option>
              </select>
            </div>
            <div>
              <label className="text-small text-muted mb-1" style={{ display: 'block' }}>
                Cross-Org Sharing
              </label>
              <label style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem',
                background: 'rgba(255, 255, 255, 0.02)',
                border: '1px solid var(--border-subtle)',
                borderRadius: '4px',
                cursor: filters.domainType ? 'pointer' : 'not-allowed',
                opacity: filters.domainType ? 1 : 0.5,
              }}>
                <input
                  type="checkbox"
                  checked={filters.includeCrossOrg}
                  onChange={(e) => setFilters({ ...filters, includeCrossOrg: e.target.checked })}
                  disabled={!filters.domainType}
                />
                <span className="text-small">Include cross-org (anonymized)</span>
              </label>
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: '0.5rem' }}>
              <button
                type="button"
                onClick={() => setFilters({
                  agentId: '',
                  outcomeType: '',
                  minScore: '',
                  maxScore: '',
                  startDate: '',
                  endDate: '',
                  domainType: '',
                  includeCrossOrg: false,
                })}
                className="btn btn-secondary"
                style={{ width: '100%' }}
              >
                Clear Filters
              </button>
            </div>
          </div>
        )}
      </form>

      {error && (
        <div className="card" style={{ background: 'rgba(255, 0, 255, 0.1)', color: 'var(--magenta)', marginBottom: '1.5rem' }}>
          {error}
        </div>
      )}

      {/* List-Detail Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: selectedTrajectory ? '400px 1fr' : '1fr', gap: '1.5rem' }}>
        {/* Trajectory list */}
        {loading && trajectories.length === 0 ? (
          <TrajectoryListSkeleton count={10} />
        ) : (
          <div style={{
            background: 'rgba(255, 255, 255, 0.01)',
            border: '1px solid var(--border-subtle)',
            overflow: 'hidden',
          }}>
            {filteredTrajectories.map((trajectory, index) => {
            const outcome = trajectory.data?.outcome;
            const metadata = trajectory.data?.metadata;
            const isSelected = selectedTrajectory === trajectory.id;

            return (
              <div
                key={trajectory.id}
                style={{
                  padding: '1rem 1.5rem',
                  cursor: 'pointer',
                  background: isSelected ? 'rgba(0, 255, 136, 0.08)' : 'transparent',
                  borderBottom: index < filteredTrajectories.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                  borderLeft: isSelected ? '3px solid var(--neon-green)' : '3px solid transparent',
                  transition: 'all 0.2s ease',
                }}
                onClick={() => selectTrajectory(trajectory.id)}
                onMouseEnter={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) {
                    e.currentTarget.style.background = 'transparent';
                  }
                }}
              >
                <div className="flex items-center gap-3 mb-2">
                  {/* Execution Status (did it complete?) */}
                  <span
                    className={`badge ${
                      (outcome?.execution?.status || outcome?.type) === 'completed' || outcome?.type === 'success'
                        ? 'badge-success'
                        : (outcome?.execution?.status || outcome?.type) === 'failed' || outcome?.type === 'failure'
                        ? 'badge-failure'
                        : 'badge-neutral'
                    }`}
                    title={`Execution status: ${outcome?.execution?.status || outcome?.type || 'unknown'}`}
                  >
                    {outcome?.execution?.status || outcome?.type || 'unknown'}
                  </span>
                  {/* Learning Value (quality score) */}
                  <span
                    className="text-small font-mono"
                    style={{ color: 'var(--neon-teal)' }}
                    title="Learning value: How valuable is this trajectory for continual learning (0-1)"
                  >
                    {trajectory.outcome_score !== null && trajectory.outcome_score !== undefined
                      ? `${['⭐'.repeat(Math.round(trajectory.outcome_score * 5))].join('')} ${trajectory.outcome_score.toFixed(2)}`
                      : 'N/A'}
                  </span>
                </div>
                {trajectory.searchable_summary && (
                  <p style={{
                    color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)',
                    lineHeight: '1.6',
                    fontSize: '0.875rem',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    marginBottom: trajectory.tags && trajectory.tags.length > 0 ? '0.5rem' : '0',
                  }}>
                    {trajectory.searchable_summary}
                  </p>
                )}
                {trajectory.tags && trajectory.tags.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', marginTop: '0.5rem' }}>
                    {trajectory.tags.slice(0, 3).map((tag, tagIdx) => (
                      <span key={tagIdx} className="badge badge-neutral" style={{ fontSize: '0.625rem', padding: '0.125rem 0.375rem' }}>
                        {tag}
                      </span>
                    ))}
                    {trajectory.tags.length > 3 && (
                      <span className="badge badge-neutral" style={{ fontSize: '0.625rem', padding: '0.125rem 0.375rem' }}>
                        +{trajectory.tags.length - 3}
                      </span>
                    )}
                  </div>
                )}
                <div className="flex justify-between items-center text-small mt-2" style={{ color: 'var(--text-tertiary)' }}>
                  <span className="font-mono">
                    {metadata?.step_count || 0} steps
                  </span>
                  <span>
                    {new Date(trajectory.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            );
          })}
          </div>
        )}

        {/* Trajectory detail panel */}
        {selectedTrajectory && (loadingDetail ? (
          <TrajectoryDetailSkeleton />
        ) : (() => {
          const trajectory = trajectories.find(t => t.id === selectedTrajectory);
          if (!trajectory) return null;

          const outcome = trajectory.data?.outcome;
          const metadata = trajectory.data?.metadata;
          const turns = trajectory.data?.turns || [];

          return (
            <div className="card" style={{ position: 'sticky', top: '1.5rem', maxHeight: 'calc(100vh - 6rem)', overflow: 'auto' }}>
              <>
                  {/* Header - Execution Status (OTS-derived) */}
                  <div style={{ marginBottom: '1.5rem', paddingBottom: '1rem', borderBottom: '1px solid var(--border-subtle)' }}>
                    <div className="flex items-center gap-3">
                      {/* Execution Status - from OTS */}
                      <span
                        className={`badge ${
                          (outcome?.execution?.status || outcome?.type) === 'completed' || outcome?.type === 'success'
                            ? 'badge-success'
                            : (outcome?.execution?.status || outcome?.type) === 'failed' || outcome?.type === 'failure'
                            ? 'badge-failure'
                            : 'badge-neutral'
                        }`}
                        title="Execution status from trajectory data"
                      >
                        Exec: {outcome?.execution?.status || outcome?.type || 'unknown'}
                      </span>
                      {/* Processing Status - shows if enrichment is done */}
                      {trajectory.processing_status && (
                        <span className={`badge ${
                          trajectory.processing_status === 'completed'
                            ? 'badge-success'
                            : trajectory.processing_status === 'failed'
                            ? 'badge-failure'
                            : 'badge-neutral'
                        }`}
                        title="Letta enrichment processing status"
                        >
                          Enrichment: {trajectory.processing_status}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* ============================================ */}
                  {/* OTS DATA SECTION - Raw trajectory extraction */}
                  {/* ============================================ */}
                  <div style={{ marginBottom: '1.5rem' }}>
                    <div style={{ marginBottom: '1rem', paddingBottom: '0.75rem', borderBottom: '1px solid rgba(255, 255, 0, 0.2)' }}>
                      <h3 style={{
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        color: 'var(--neon-lemon)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        marginBottom: '0.25rem'
                      }}>
                        OTS Data
                      </h3>
                      <p className="text-small" style={{ color: 'var(--text-tertiary)' }}>
                        Extracted directly from agent execution — no LLM processing
                      </p>
                    </div>

                    {/* OTS Decisions */}
                    {trajectory.decisions && trajectory.decisions.length > 0 && (
                      <div style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
                        <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span style={{ color: 'var(--neon-lemon)' }}>🎯</span> Decisions ({trajectory.decisions.length})
                        </h4>
                        <div className="text-small text-muted" style={{ marginBottom: '1rem' }}>
                          Tool calls extracted as OTS-style decisions with success/failure analysis
                        </div>

                        {/* Decision Summary */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.75rem', marginBottom: '1rem' }}>
                          <div style={{ padding: '0.5rem', background: 'rgba(0, 255, 136, 0.05)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                            <div className="font-mono" style={{ color: 'var(--neon-green)', fontSize: '1.25rem' }}>
                              {trajectory.decisions.filter(d => d.success).length}
                            </div>
                            <div className="text-small text-muted">Successful</div>
                          </div>
                          <div style={{ padding: '0.5rem', background: 'rgba(255, 0, 255, 0.05)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                            <div className="font-mono" style={{ color: 'var(--neon-magenta)', fontSize: '1.25rem' }}>
                              {trajectory.decisions.filter(d => !d.success).length}
                            </div>
                            <div className="text-small text-muted">Failed</div>
                          </div>
                          <div style={{ padding: '0.5rem', background: 'rgba(0, 229, 255, 0.05)', border: '1px solid var(--border-subtle)', textAlign: 'center' }}>
                            <div className="font-mono" style={{ color: 'var(--neon-teal)', fontSize: '1.25rem' }}>
                              {trajectory.decisions.length > 0
                                ? Math.round((trajectory.decisions.filter(d => d.success).length / trajectory.decisions.length) * 100)
                                : 0}%
                            </div>
                            <div className="text-small text-muted">Success Rate</div>
                          </div>
                        </div>

                        {/* Decision List */}
                        <div style={{ display: 'grid', gap: '0.5rem' }}>
                          {trajectory.decisions.map((decision, idx) => (
                            <div key={decision.decision_id || idx} style={{
                              padding: '0.75rem',
                              background: decision.success ? 'rgba(0, 255, 136, 0.03)' : 'rgba(255, 0, 255, 0.05)',
                              border: `1px solid ${decision.success ? 'rgba(0, 255, 136, 0.2)' : 'rgba(255, 0, 255, 0.3)'}`,
                            }}>
                              <div className="flex justify-between items-center mb-2">
                                <div className="flex items-center gap-2">
                                  <span className="font-mono text-small" style={{ color: 'var(--neon-magenta)' }}>
                                    {decision.action}
                                  </span>
                                  <span className={`badge ${decision.success ? 'badge-success' : 'badge-failure'}`} style={{ fontSize: '0.625rem' }}>
                                    {decision.success ? '✓ Success' : '✗ Failed'}
                                  </span>
                                </div>
                                <span className="text-small text-muted">Turn {decision.turn_index + 1}</span>
                              </div>

                              {decision.error_type && (
                                <div className="text-small" style={{ color: 'var(--neon-magenta)', marginBottom: '0.5rem' }}>
                                  Error: {decision.error_type}
                                </div>
                              )}

                              {decision.arguments && Object.keys(decision.arguments).length > 0 && (
                                <div style={{ marginTop: '0.5rem' }}>
                                  <div className="text-small text-muted mb-1">Arguments:</div>
                                  <pre style={{
                                    fontSize: '0.7rem',
                                    color: 'var(--text-tertiary)',
                                    background: 'rgba(0, 0, 0, 0.3)',
                                    padding: '0.5rem',
                                    margin: 0,
                                    overflow: 'auto',
                                    maxHeight: '100px',
                                    whiteSpace: 'pre-wrap',
                                    wordBreak: 'break-word',
                                  }}>
                                    {typeof decision.arguments === 'string'
                                      ? decision.arguments
                                      : JSON.stringify(decision.arguments, null, 2).slice(0, 300)}
                                    {JSON.stringify(decision.arguments).length > 300 && '...'}
                                  </pre>
                                </div>
                              )}

                              {decision.result_summary && (
                                <div style={{ marginTop: '0.5rem' }}>
                                  <div className="text-small text-muted mb-1">Result:</div>
                                  <div className="text-small" style={{
                                    color: 'var(--text-secondary)',
                                    background: 'rgba(0, 0, 0, 0.2)',
                                    padding: '0.5rem',
                                    maxHeight: '60px',
                                    overflow: 'auto',
                                  }}>
                                    {decision.result_summary}
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Metadata (OTS) */}
                    {metadata && (
                      <div style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
                        <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem' }}>
                          Execution Metadata
                        </h4>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                          <div>
                            <div className="text-small text-muted mb-1">Steps</div>
                            <div className="font-mono" style={{ color: 'var(--text-secondary)' }}>{metadata.step_count}</div>
                          </div>
                          <div>
                            <div className="text-small text-muted mb-1">Messages</div>
                            <div className="font-mono" style={{ color: 'var(--text-secondary)' }}>{metadata.message_count}</div>
                          </div>
                          <div>
                            <div className="text-small text-muted mb-1">Total Tokens</div>
                            <div className="font-mono" style={{ color: 'var(--text-secondary)' }}>{metadata.total_tokens?.toLocaleString()}</div>
                          </div>
                          <div>
                            <div className="text-small text-muted mb-1">Duration</div>
                            <div className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                              {metadata.duration_ns ? `${(metadata.duration_ns / 1_000_000_000).toFixed(1)}s` : 'N/A'}
                            </div>
                          </div>
                          <div>
                            <div className="text-small text-muted mb-1">Status</div>
                            <span className="badge badge-neutral">{metadata.status}</span>
                          </div>
                          <div>
                            <div className="text-small text-muted mb-1">Run ID</div>
                            <div className="font-mono text-small" style={{ color: 'var(--text-tertiary)', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                              {trajectory.data?.run_id?.slice(0, 12)}...
                            </div>
                          </div>
                        </div>
                        {metadata.models && metadata.models.length > 0 && (
                          <div style={{ marginTop: '1rem' }}>
                            <div className="text-small text-muted mb-2">Models</div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                              {metadata.models.map((model, idx) => (
                                <span key={idx} className="badge badge-neutral text-small font-mono">
                                  {model}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {metadata.tools_used && metadata.tools_used.length > 0 && (
                          <div style={{ marginTop: '1rem' }}>
                            <div className="text-small text-muted mb-2">Tools Used</div>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                              {metadata.tools_used.map((tool, idx) => (
                                <span key={idx} className="badge badge-neutral text-small font-mono" style={{ color: 'var(--neon-magenta)' }}>
                                  {tool}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Execution Turns (OTS) */}
                    {turns.length > 0 && (
                      <div style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
                        <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem' }}>
                          Execution Trace ({turns.length} turns)
                        </h4>
                        <div style={{ display: 'grid', gap: '1rem' }}>
                          {turns.map((turn, idx) => (
                            <div key={turn.step_id || idx} style={{
                              padding: '1rem',
                              background: 'rgba(255, 255, 255, 0.02)',
                              border: '1px solid var(--border-subtle)',
                            }}>
                              <div className="flex justify-between items-center mb-3">
                                <span className="font-mono" style={{ color: 'var(--neon-green)' }}>
                                  Turn {idx + 1}
                                </span>
                                <div className="flex items-center gap-3 text-small" style={{ color: 'var(--text-tertiary)' }}>
                                  <span className="font-mono">{turn.model}</span>
                                  <span>•</span>
                                  <span className="font-mono">{(turn.input_tokens || 0) + (turn.output_tokens || 0)} tokens</span>
                                </div>
                              </div>
                              {Array.isArray(turn.messages) && turn.messages.length > 0 && (
                                <div style={{ display: 'grid', gap: '0.75rem' }}>
                                  {turn.messages.map((msg: any, msgIdx: number) => (
                                    <div key={msgIdx} style={{
                                      padding: '0.75rem',
                                      background: msg.role === 'user' ? 'rgba(0, 229, 255, 0.05)' : 'rgba(0, 255, 136, 0.05)',
                                      border: `1px solid ${msg.role === 'user' ? 'rgba(0, 229, 255, 0.2)' : 'rgba(0, 255, 136, 0.2)'}`,
                                    }}>
                                      <div className="flex justify-between items-center mb-2">
                                        <span className={`badge ${msg.role === 'user' ? 'badge-neutral' : 'badge-success'}`}>
                                          {msg.role}
                                        </span>
                                        {msg.tool_calls && msg.tool_calls.length > 0 && (
                                          <span className="text-small font-mono" style={{ color: 'var(--neon-magenta)' }}>
                                            {msg.tool_calls.length} tool call{msg.tool_calls.length > 1 ? 's' : ''}
                                          </span>
                                        )}
                                      </div>
                                      {/* Handle text content - could be string or array of content blocks */}
                                      {msg.text && (
                                        <div style={{
                                          color: 'var(--text-secondary)',
                                          fontSize: '0.875rem',
                                          lineHeight: '1.7',
                                          whiteSpace: 'pre-wrap',
                                          wordBreak: 'break-word',
                                        }}>
                                          {typeof msg.text === 'string' ? msg.text : JSON.stringify(msg.text)}
                                        </div>
                                      )}
                                      {/* Also check for content field which might contain the actual message */}
                                      {!msg.text && msg.content && (
                                        <div style={{
                                          color: 'var(--text-secondary)',
                                          fontSize: '0.875rem',
                                          lineHeight: '1.7',
                                          whiteSpace: 'pre-wrap',
                                          wordBreak: 'break-word',
                                        }}>
                                          {typeof msg.content === 'string'
                                            ? msg.content
                                            : Array.isArray(msg.content)
                                              ? msg.content.map((c: any) => c.text || c.content || '').filter(Boolean).join('\n')
                                              : JSON.stringify(msg.content)}
                                        </div>
                                      )}
                                      {msg.tool_calls && msg.tool_calls.length > 0 && (
                                        <div style={{ marginTop: '0.75rem' }}>
                                          {msg.tool_calls.map((tc: any, tcIdx: number) => (
                                            <div key={tcIdx} style={{
                                              padding: '0.5rem',
                                              background: 'rgba(0, 0, 0, 0.3)',
                                              border: '1px solid var(--border-subtle)',
                                              marginBottom: tcIdx < msg.tool_calls!.length - 1 ? '0.5rem' : 0,
                                            }}>
                                              <div className="font-mono text-small" style={{ color: 'var(--neon-magenta)', marginBottom: '0.25rem' }}>
                                                {tc.function?.name || tc.name || 'unknown'}
                                              </div>
                                              <pre style={{
                                                fontSize: '0.75rem',
                                                color: 'var(--text-tertiary)',
                                                whiteSpace: 'pre-wrap',
                                                wordBreak: 'break-word',
                                                margin: 0,
                                              }}>
                                                {tc.function?.arguments || tc.arguments || '{}'}
                                              </pre>
                                            </div>
                                          ))}
                                        </div>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Raw OTS JSON - Collapsible */}
                    {trajectory.data && (
                      <details style={{ marginTop: '1rem' }}>
                        <summary style={{
                          cursor: 'pointer',
                          padding: '0.75rem',
                          background: 'rgba(255, 255, 0, 0.05)',
                          border: '1px solid rgba(255, 255, 0, 0.2)',
                          color: 'var(--neon-lemon)',
                          fontSize: '0.875rem',
                          fontWeight: 600,
                          userSelect: 'none',
                        }}>
                          📄 View Raw OTS JSON
                        </summary>
                        <div style={{
                          padding: '1rem',
                          background: 'rgba(0, 0, 0, 0.4)',
                          border: '1px solid var(--border-subtle)',
                          borderTop: 'none',
                          maxHeight: '400px',
                          overflow: 'auto',
                        }}>
                          <pre style={{
                            fontSize: '0.75rem',
                            color: 'var(--text-secondary)',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-word',
                            margin: 0,
                            fontFamily: 'var(--font-mono)',
                          }}>
                            {JSON.stringify(trajectory.data, null, 2)}
                          </pre>
                        </div>
                      </details>
                    )}
                  </div>

                  {/* ============================================ */}
                  {/* LETTA-ENRICHED SECTION - LLM-processed data */}
                  {/* ============================================ */}
                  <div style={{ marginBottom: '1.5rem' }}>
                    <div style={{ marginBottom: '1rem', paddingBottom: '0.75rem', borderBottom: '1px solid rgba(255, 0, 255, 0.2)' }}>
                      <h3 style={{
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        color: 'var(--neon-magenta)',
                        textTransform: 'uppercase',
                        letterSpacing: '0.05em',
                        marginBottom: '0.25rem'
                      }}>
                        Letta-Enriched Data
                      </h3>
                      <p className="text-small" style={{ color: 'var(--text-tertiary)' }}>
                        Semantic analysis using <span style={{ color: 'var(--neon-magenta)', fontFamily: 'var(--font-mono)' }}>gpt-4o-mini</span>
                      </p>
                    </div>

                    {/* Learning Score (Letta-enriched via LLM) */}
                    {(trajectory.outcome_score !== null && trajectory.outcome_score !== undefined) && (
                      <div style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
                        <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem' }}>
                          Learning Value Score
                        </h4>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                          <span className="font-mono" style={{ fontSize: '1.5rem', color: 'var(--neon-teal)' }}>
                            {trajectory.outcome_score.toFixed(2)}
                          </span>
                          <span style={{ fontSize: '1.25rem' }}>
                            {'⭐'.repeat(Math.round(trajectory.outcome_score * 5))}
                          </span>
                        </div>
                        <p className="text-small text-muted" style={{ marginTop: '0.5rem' }}>
                          Quality score (0-1) generated by LLM based on interaction depth, task complexity, and learning value
                        </p>
                      </div>
                    )}

                    {/* Summary and Tags (Letta-enriched) */}
                    {(trajectory.searchable_summary || trajectory.tags || trajectory.task_category || trajectory.complexity_level) && (
                      <div style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
                        {trajectory.searchable_summary && (
                          <div style={{ marginBottom: '1rem' }}>
                            <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.5rem' }}>
                              Summary
                            </h4>
                            <p style={{ color: 'var(--text-secondary)', lineHeight: '1.7', fontSize: '0.9375rem' }}>
                              {trajectory.searchable_summary}
                            </p>
                          </div>
                        )}

                        {/* Tags, Category, Complexity */}
                        {(trajectory.tags || trajectory.task_category || trajectory.complexity_level) && (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
                            {trajectory.task_category && (
                              <span className="badge" style={{ background: 'rgba(0, 229, 255, 0.1)', color: 'var(--neon-teal)', border: '1px solid rgba(0, 229, 255, 0.3)' }}>
                                📑 {trajectory.task_category}
                              </span>
                            )}
                            {trajectory.complexity_level && (
                              <span className="badge" style={{ background: 'rgba(255, 255, 0, 0.1)', color: 'var(--neon-lemon)', border: '1px solid rgba(255, 255, 0, 0.3)' }}>
                                🎯 {trajectory.complexity_level}
                              </span>
                            )}
                            {trajectory.tags && trajectory.tags.length > 0 && trajectory.tags.map((tag, idx) => (
                              <span key={idx} className="badge badge-neutral" style={{ fontSize: '0.75rem' }}>
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                    {/* LLM Processing Details (Letta-enriched) */}
                  {(trajectory.score_reasoning || trajectory.processing_completed_at) && (
                    <div style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
                      <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ color: 'var(--neon-magenta)' }}>🤖</span> LLM Processing
                      </h4>

                      <div style={{ display: 'grid', gap: '1rem' }}>
                        {/* Processing Model */}
                        <div style={{ padding: '0.75rem', background: 'rgba(255, 0, 255, 0.05)', border: '1px solid var(--border-subtle)' }}>
                          <div className="text-small text-muted mb-1">Processed by</div>
                          <div className="font-mono" style={{ color: 'var(--neon-magenta)' }}>gpt-4o-mini</div>
                          <div className="text-small" style={{ color: 'var(--text-tertiary)', marginTop: '0.25rem' }}>
                            OpenAI's fast model for trajectory analysis
                          </div>
                        </div>

                        {/* Processing Duration */}
                        {trajectory.processing_started_at && trajectory.processing_completed_at && (
                          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
                            <div>
                              <div className="text-small text-muted mb-1">Processing Time</div>
                              <div className="font-mono text-small" style={{ color: 'var(--text-secondary)' }}>
                                {(() => {
                                  const start = new Date(trajectory.processing_started_at!);
                                  const end = new Date(trajectory.processing_completed_at!);
                                  const durationMs = end.getTime() - start.getTime();
                                  return `${(durationMs / 1000).toFixed(1)}s`;
                                })()}
                              </div>
                            </div>
                            <div>
                              <div className="text-small text-muted mb-1">Completed</div>
                              <div className="text-small" style={{ color: 'var(--text-secondary)' }}>
                                {new Date(trajectory.processing_completed_at).toLocaleString()}
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Score Reasoning */}
                        {trajectory.score_reasoning && (
                          <div>
                            <div className="text-small" style={{ color: 'var(--neon-green)', marginBottom: '0.5rem', fontWeight: 600 }}>
                              Score Reasoning (Learning Value Assessment)
                            </div>
                            <div style={{
                              padding: '0.75rem',
                              background: 'rgba(0, 255, 136, 0.05)',
                              border: '1px solid var(--border-subtle)',
                              color: 'var(--text-secondary)',
                              fontSize: '0.875rem',
                              lineHeight: '1.7'
                            }}>
                              {trajectory.score_reasoning}
                            </div>
                            <div className="text-small text-muted" style={{ marginTop: '0.5rem', fontStyle: 'italic' }}>
                              Scored based on: interaction depth (35%), task complexity (30%), tool usage (20%), learning value (15%)
                            </div>
                          </div>
                        )}

                        {trajectory.processing_error && (
                          <div style={{ padding: '0.75rem', background: 'rgba(255, 0, 255, 0.1)', border: '1px solid var(--neon-magenta)', color: 'var(--neon-magenta)' }}>
                            <div className="text-small font-mono">Processing Error:</div>
                            <div className="text-small" style={{ marginTop: '0.25rem' }}>{trajectory.processing_error}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                    {/* Outcome Analysis (Letta-enriched) */}
                    {outcome && (
                      <div style={{ marginBottom: '1.5rem' }}>
                        <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem' }}>
                          Outcome Analysis
                        </h4>
                        {outcome.confidence !== undefined && (
                          <div style={{ marginBottom: '1rem' }}>
                            <div className="text-small text-muted mb-1">Confidence</div>
                            <div className="font-mono" style={{ color: 'var(--neon-teal)' }}>
                              {(outcome.confidence * 100).toFixed(0)}%
                            </div>
                          </div>
                        )}
                        {outcome.reasoning && outcome.reasoning.length > 0 && (
                          <div>
                            <div className="text-small text-muted mb-2">Reasoning</div>
                            <ul style={{ paddingLeft: '1.25rem', color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: '1.7' }}>
                              {outcome.reasoning.map((reason, idx) => (
                                <li key={idx} style={{ marginBottom: '0.5rem' }}>{reason}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Footer */}
                  <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-subtle)' }}>
                    <div className="text-small text-muted font-mono">
                      ID: {trajectory.id}
                    </div>
                    <div className="text-small text-muted" style={{ marginTop: '0.25rem' }}>
                      Created: {new Date(trajectory.created_at).toLocaleString()}
                    </div>
                  </div>
                </>
            </div>
          );
        })())}
      </div>

      {/* Pagination */}
      <div style={{
        marginTop: '1.5rem',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: '1rem',
      }}>
        <button
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page === 1}
          className="btn btn-secondary"
        >
          Previous
        </button>
        <span className="text-small text-muted font-mono">
          Page {page}
        </span>
        <button
          onClick={() => setPage(p => p + 1)}
          disabled={filteredTrajectories.length < pageSize}
          className="btn btn-secondary"
        >
          Next
        </button>
      </div>

      {filteredTrajectories.length === 0 && !loading && (
        <div className="empty-state">No trajectories found</div>
      )}
          </div>
        </Tabs.Content>

        <Tabs.Content value="analytics">
          <AnalyticsView />
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
