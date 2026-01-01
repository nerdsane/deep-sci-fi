import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import type { Agent } from '../types/letta';

interface AgentWithDetails extends Agent {
  tools?: any[];
  memory?: any;
  messages?: any[];
}

export function AgentsView() {
  const [agents, setAgents] = useState<AgentWithDetails[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [loadingDetails, setLoadingDetails] = useState<string | null>(null);

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

  async function loadAgentDetails(agentId: string) {
    if (expandedAgent === agentId) {
      setExpandedAgent(null);
      return;
    }

    try {
      setLoadingDetails(agentId);
      const [tools, memory, messages] = await Promise.allSettled([
        api.listTools().then(res => (Array.isArray(res) ? res : res.items || [])),
        api.getCoreMemory(agentId),
        api.getAgentMessages(agentId, 5),
      ]);

      setAgents(prevAgents =>
        prevAgents.map(agent =>
          agent.id === agentId
            ? {
                ...agent,
                tools: tools.status === 'fulfilled' ? tools.value : null,
                memory: memory.status === 'fulfilled' ? memory.value : null,
                messages: messages.status === 'fulfilled'
                  ? (Array.isArray(messages.value) ? messages.value : messages.value.items || [])
                  : null,
              }
            : agent
        )
      );
      setExpandedAgent(agentId);
    } catch (err) {
      console.error('Failed to load agent details:', err);
    } finally {
      setLoadingDetails(null);
    }
  }

  if (loading) {
    return <div className="loading">Loading agents...</div>;
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
        <h2 className="section-title">Agents</h2>
        <p className="section-subtitle">
          {agents.length} active {agents.length === 1 ? 'agent' : 'agents'}
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: expandedAgent ? '1fr 1.5fr' : '1fr', gap: '1.5rem' }}>
        {/* Agent list */}
        <div className="card-list">
          {agents.map((agent) => {
            const isSelected = expandedAgent === agent.id;
            const isLoading = loadingDetails === agent.id;

            return (
              <div
                key={agent.id}
                className="card"
                style={{
                  cursor: 'pointer',
                  background: isSelected ? 'rgba(0, 255, 136, 0.05)' : 'rgba(255, 255, 255, 0.02)',
                  borderColor: isSelected ? 'var(--border-accent)' : 'var(--border-subtle)',
                }}
                onClick={() => !isLoading && loadAgentDetails(agent.id)}
              >
                <div className="flex justify-between items-start">
                  <div style={{ flex: 1 }}>
                    <h3 style={{ fontSize: '1.125rem', marginBottom: '0.5rem', color: 'var(--text-primary)', fontWeight: 600 }}>
                      {agent.name}
                    </h3>
                    {agent.description && (
                      <p style={{ color: 'var(--text-secondary)', lineHeight: '1.6', fontSize: '0.875rem', marginBottom: '0.75rem' }}>
                        {agent.description.slice(0, 120)}{agent.description.length > 120 ? '...' : ''}
                      </p>
                    )}
                    <div className="flex gap-3 items-center text-small" style={{ marginTop: '0.75rem' }}>
                      <span className="font-mono" style={{ color: 'var(--text-tertiary)' }}>{agent.model}</span>
                      <span className="badge badge-neutral text-small">{agent.agent_type}</span>
                    </div>
                  </div>
                </div>
                {isLoading && (
                  <div className="text-small text-muted" style={{ marginTop: '0.75rem' }}>Loading...</div>
                )}
              </div>
            );
          })}
        </div>

        {/* Agent details panel */}
        {expandedAgent && (() => {
          const agent = agents.find(a => a.id === expandedAgent);
          if (!agent) return null;

          return (
            <div className="card" style={{ position: 'sticky', top: '1.5rem', maxHeight: 'calc(100vh - 6rem)', overflow: 'auto' }}>
              <div style={{ marginBottom: '1.5rem' }}>
                <h3 style={{ fontSize: '1.5rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.75rem' }}>
                  {agent.name}
                </h3>
                {agent.description && (
                  <p style={{ color: 'var(--text-secondary)', lineHeight: '1.7', fontSize: '0.9375rem' }}>
                    {agent.description}
                  </p>
                )}
              </div>

              {/* Basic Info */}
              <div style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
                  <div>
                    <div className="text-small text-muted mb-1">Model</div>
                    <div className="font-mono" style={{ color: 'var(--neon-teal)' }}>{agent.model}</div>
                  </div>
                  <div>
                    <div className="text-small text-muted mb-1">Type</div>
                    <span className="badge badge-neutral">{agent.agent_type}</span>
                  </div>
                  <div>
                    <div className="text-small text-muted mb-1">ID</div>
                    <div className="font-mono text-small" style={{ color: 'var(--text-tertiary)' }}>{agent.id}</div>
                  </div>
                  <div>
                    <div className="text-small text-muted mb-1">Created</div>
                    <div className="text-small" style={{ color: 'var(--text-secondary)' }}>
                      {new Date(agent.created_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                    </div>
                  </div>
                </div>
                {agent.tags && agent.tags.length > 0 && (
                  <div style={{ marginTop: '1rem' }}>
                    <div className="text-small text-muted mb-2">Tags</div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                      {agent.tags.map((tag) => (
                        <span key={tag} className="badge badge-neutral text-small">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Core Memory */}
              {agent.memory && (
                <div style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
                  <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem' }}>
                    Core Memory
                  </h4>
                  {agent.memory.blocks && agent.memory.blocks.length > 0 ? (
                    <div style={{ display: 'grid', gap: '1rem' }}>
                      {agent.memory.blocks.map((block: any) => (
                        <div key={block.id || block.label} style={{
                          padding: '1rem',
                          background: 'rgba(0, 255, 136, 0.03)',
                          border: '1px solid var(--border-subtle)',
                        }}>
                          <div className="font-mono" style={{ color: 'var(--neon-green)', marginBottom: '0.75rem', fontWeight: 600 }}>
                            {block.label || 'Memory Block'}
                          </div>
                          <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: '1.7', whiteSpace: 'pre-wrap' }}>
                            {block.value || 'No content'}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="text-small text-muted">No memory blocks</div>
                  )}
                </div>
              )}

              {/* Tools */}
              {agent.tools && agent.tools.length > 0 && (
                <div style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
                  <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem' }}>
                    Tools ({agent.tools.length})
                  </h4>
                  <div style={{ display: 'grid', gap: '0.75rem' }}>
                    {agent.tools.map((tool: any, idx: number) => (
                      <div key={tool.id || idx} style={{
                        padding: '0.75rem',
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid var(--border-subtle)',
                      }}>
                        <div className="font-mono text-small" style={{ color: 'var(--neon-magenta)' }}>
                          {tool.name}
                        </div>
                        {tool.description && (
                          <div className="text-small" style={{ color: 'var(--text-tertiary)', marginTop: '0.25rem' }}>
                            {tool.description}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recent Messages */}
              {agent.messages && agent.messages.length > 0 && (
                <div>
                  <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem' }}>
                    Recent Messages ({agent.messages.length})
                  </h4>
                  <div style={{ display: 'grid', gap: '1rem' }}>
                    {agent.messages.map((msg: any) => (
                      <div key={msg.id} style={{
                        padding: '1rem',
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid var(--border-subtle)',
                      }}>
                        <div className="flex justify-between items-center mb-2">
                          <span className={`badge badge-${msg.role === 'user' ? 'neutral' : 'success'}`}>
                            {msg.role}
                          </span>
                          <span className="text-small text-muted">
                            {new Date(msg.created_at).toLocaleString()}
                          </span>
                        </div>
                        <div style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: '1.7', whiteSpace: 'pre-wrap' }}>
                          {msg.text || msg.content || 'No content'}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })()}
      </div>

      {agents.length === 0 && (
        <div className="empty-state">No agents found</div>
      )}
    </div>
  );
}
