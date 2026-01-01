import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';

interface Step {
  id: string;
  run_id: string;
  agent_id?: string;
  status: string;
  step_type?: string;
  created_at: string;
  completed_at?: string;
  metadata?: any;
}

export function StepsView() {
  const [steps, setSteps] = useState<Step[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedStep, setSelectedStep] = useState<string | null>(null);
  const [stepDetails, setStepDetails] = useState<any>(null);

  useEffect(() => {
    loadSteps();
  }, []);

  async function loadSteps() {
    try {
      setLoading(true);
      const response = await api.listSteps(100);
      setSteps(Array.isArray(response) ? response : response.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load steps');
    } finally {
      setLoading(false);
    }
  }

  async function loadStepDetails(stepId: string) {
    try {
      setSelectedStep(stepId);
      const [stepData, metrics] = await Promise.allSettled([
        api.getStep(stepId),
        api.getStepMetrics(stepId),
      ]);

      setStepDetails({
        step: stepData.status === 'fulfilled' ? stepData.value : null,
        metrics: metrics.status === 'fulfilled' ? metrics.value : null,
      });
    } catch (err) {
      console.error('Failed to load step details:', err);
    }
  }

  const completedSteps = steps.filter(s => s.status === 'completed').length;
  const failedSteps = steps.filter(s => s.status === 'failed').length;

  if (loading) {
    return <div className="loading">Loading steps...</div>;
  }

  return (
    <div>
      <div>
        <h2 className="section-title">Steps</h2>
        <p className="section-subtitle">
          Detailed execution steps from agent runs
        </p>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value color-teal">{steps.length}</div>
          <div className="stat-label">Total Steps</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-green">{completedSteps}</div>
          <div className="stat-label">Completed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-magenta">{failedSteps}</div>
          <div className="stat-label">Failed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-lemon">
            {steps.length > 0 ? Math.round((completedSteps / steps.length) * 100) : 0}%
          </div>
          <div className="stat-label">Success Rate</div>
        </div>
      </div>

      {error && (
        <div className="card" style={{ background: 'rgba(255, 0, 255, 0.1)', color: 'var(--magenta)', marginBottom: '1.5rem' }}>
          {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: selectedStep ? '1fr 1fr' : '1fr', gap: '1.5rem' }}>
        {/* Step list */}
        <div className="card-list">
          {steps.map((step) => {
            const duration = step.completed_at
              ? (new Date(step.completed_at).getTime() - new Date(step.created_at).getTime()) / 1000
              : null;

            return (
              <div
                key={step.id}
                className="card"
                style={{
                  cursor: 'pointer',
                  background: selectedStep === step.id ? 'rgba(0, 255, 136, 0.05)' : 'rgba(255, 255, 255, 0.02)',
                }}
                onClick={() => loadStepDetails(step.id)}
              >
                <div className="flex justify-between items-start">
                  <div style={{ flex: 1 }}>
                    <div className="flex items-center gap-3 mb-2">
                      <span className="font-mono text-small" style={{ color: 'var(--text-primary)' }}>
                        {step.id.slice(0, 12)}...
                      </span>
                      <span
                        className={`badge ${
                          step.status === 'completed'
                            ? 'badge-success'
                            : step.status === 'failed'
                            ? 'badge-failure'
                            : step.status === 'running'
                            ? 'badge-running'
                            : 'badge-neutral'
                        }`}
                      >
                        {step.status}
                      </span>
                      {step.step_type && (
                        <span className="badge badge-neutral text-small">{step.step_type}</span>
                      )}
                    </div>
                    <div className="text-small text-muted font-mono">
                      Run: {step.run_id.slice(0, 12)}...
                    </div>
                    {duration !== null && (
                      <div className="text-small text-muted mt-1">
                        Duration: {duration.toFixed(2)}s
                      </div>
                    )}
                  </div>
                  <div className="text-small text-muted">
                    {new Date(step.created_at).toLocaleString()}
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        {/* Step details panel */}
        {selectedStep && stepDetails && (
          <div className="card" style={{ position: 'sticky', top: '1.5rem', maxHeight: 'calc(100vh - 6rem)', overflow: 'auto' }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1.5rem' }}>
              Step Details
            </h3>

            {stepDetails.step && (
              <div style={{ marginBottom: '1.5rem' }}>
                <div className="text-small text-muted mb-2">Step Data</div>
                <pre style={{
                  background: 'rgba(0, 0, 0, 0.3)',
                  padding: '1rem',
                  borderRadius: '0',
                  overflow: 'auto',
                  fontSize: '0.75rem',
                  color: 'var(--text-secondary)',
                  lineHeight: '1.5',
                }}>
                  {JSON.stringify(stepDetails.step, null, 2)}
                </pre>
              </div>
            )}

            {stepDetails.metrics && (
              <div>
                <div className="text-small text-muted mb-2">Metrics</div>
                <div style={{ display: 'grid', gap: '0.75rem' }}>
                  {Object.entries(stepDetails.metrics).map(([key, value]) => (
                    <div key={key} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.5rem', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--border-subtle)' }}>
                      <span className="text-small text-muted">{key}:</span>
                      <span className="font-mono text-small" style={{ color: 'var(--text-primary)' }}>
                        {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {steps.length === 0 && !loading && (
        <div className="empty-state">No steps found</div>
      )}
    </div>
  );
}
