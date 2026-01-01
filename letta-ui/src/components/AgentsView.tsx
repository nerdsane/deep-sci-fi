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
      <div className="flex justify-between items-center mb-4">
        <div>
          <h2 className="section-title">Agents</h2>
          <p className="section-subtitle">
            {agents.length} active {agents.length === 1 ? 'agent' : 'agents'}
          </p>
        </div>
      </div>

      <div className="card-grid">
        {agents.map((agent) => {
          const isExpanded = expandedAgent === agent.id;
          const isLoading = loadingDetails === agent.id;

          return (
            <div
              key={agent.id}
              className="card"
              style={{ cursor: 'pointer' }}
              onClick={() => !isLoading && loadAgentDetails(agent.id)}
            >
              <div className="flex justify-between items-start mb-3">
                <div style={{ flex: 1 }}>
                  <h3 style={{ fontSize: '1.125rem', marginBottom: '0.5rem', color: 'var(--text-primary)', fontWeight: 600 }}>
                    {agent.name}
                  </h3>
                  {agent.description && (
                    <p style={{ color: 'var(--text-secondary)', lineHeight: '1.6', marginBottom: '1rem', fontSize: '0.9375rem' }}>
                      {agent.description}
                    </p>
                  )}
                </div>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div className="flex gap-2 items-center text-small">
                  <span className="text-muted" style={{ fontWeight: 500 }}>Model:</span>
                  <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{agent.model}</span>
                </div>
                <div className="flex gap-2 items-center text-small">
                  <span className="text-muted" style={{ fontWeight: 500 }}>Type:</span>
                  <span className="badge badge-neutral">{agent.agent_type}</span>
                </div>
                {agent.tags && agent.tags.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.5rem' }}>
                    {agent.tags.map((tag) => (
                      <span key={tag} className="badge badge-neutral text-small">
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {isLoading && (
                <div className="text-small text-muted" style={{ marginTop: '1rem' }}>Loading details...</div>
              )}

              {isExpanded && agent.memory && (
                <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-subtle)' }}>
                  <div className="text-small text-muted mb-2">Core Memory</div>
                  {agent.memory.blocks && agent.memory.blocks.length > 0 ? (
                    <div style={{ display: 'grid', gap: '0.75rem' }}>
                      {agent.memory.blocks.slice(0, 3).map((block: any) => (
                        <div key={block.id || block.label} style={{
                          padding: '0.75rem',
                          background: 'rgba(0, 255, 136, 0.02)',
                          border: '1px solid var(--border-subtle)',
                          fontSize: '0.75rem',
                        }}>
                          <div className="font-mono text-small" style={{ color: 'var(--neon-green)', marginBottom: '0.5rem' }}>
                            {block.label || 'Memory Block'}
                          </div>
                          <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', lineHeight: '1.5' }}>
                            {(block.value || '').slice(0, 150)}{(block.value || '').length > 150 ? '...' : ''}
                          </div>
                        </div>
                      ))}
                      {agent.memory.blocks.length > 3 && (
                        <div className="text-small text-muted">+ {agent.memory.blocks.length - 3} more blocks</div>
                      )}
                    </div>
                  ) : (
                    <div className="text-small text-muted">No memory blocks</div>
                  )}
                </div>
              )}

              {isExpanded && agent.tools && agent.tools.length > 0 && (
                <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-subtle)' }}>
                  <div className="text-small text-muted mb-2">Tools ({agent.tools.length})</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {agent.tools.slice(0, 8).map((tool: any, idx: number) => (
                      <span key={tool.id || idx} className="badge badge-neutral text-small font-mono">
                        {tool.name}
                      </span>
                    ))}
                    {agent.tools.length > 8 && (
                      <span className="text-small text-muted">+{agent.tools.length - 8} more</span>
                    )}
                  </div>
                </div>
              )}

              {isExpanded && agent.messages && agent.messages.length > 0 && (
                <div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '1px solid var(--border-subtle)' }}>
                  <div className="text-small text-muted mb-2">Recent Messages ({agent.messages.length})</div>
                  <div style={{ display: 'grid', gap: '0.5rem' }}>
                    {agent.messages.slice(0, 3).map((msg: any) => (
                      <div key={msg.id} style={{
                        padding: '0.75rem',
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid var(--border-subtle)',
                        fontSize: '0.75rem',
                      }}>
                        <div className="flex justify-between items-center mb-1">
                          <span className={`badge badge-${msg.role === 'user' ? 'neutral' : 'success'}`}>
                            {msg.role}
                          </span>
                        </div>
                        <div style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', lineHeight: '1.5' }}>
                          {((msg.text || msg.content || '').slice(0, 100))}{(msg.text || msg.content || '').length > 100 ? '...' : ''}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}>
                <span className="text-small text-muted">
                  Created {new Date(agent.created_at).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  })}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {agents.length === 0 && (
        <div className="empty-state">No agents found</div>
      )}
    </div>
  );
}
