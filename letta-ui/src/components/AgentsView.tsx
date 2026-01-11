import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import type { Agent } from '../types/letta';

interface AgentWithDetails extends Agent {
  tools?: any[];
  memory?: any;
  messages?: any[];
  llm_config?: {
    model?: string;
    context_window?: number;
  };
  embedding_config?: {
    embedding_model?: string;
    embedding_dim?: number;
  };
}

interface AgentsViewProps {
  initialSelectedAgentId?: string | null;
  onAgentSelected?: () => void;
}

export function AgentsView({ initialSelectedAgentId, onAgentSelected }: AgentsViewProps = {}) {
  const [agents, setAgents] = useState<AgentWithDetails[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [loadingDetails, setLoadingDetails] = useState<string | null>(null);
  const [editingAgent, setEditingAgent] = useState<{ id: string; name: string } | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  useEffect(() => {
    loadAgents();
  }, []);

  // Handle initial selection from external navigation
  useEffect(() => {
    if (initialSelectedAgentId && agents.length > 0 && expandedAgent !== initialSelectedAgentId) {
      loadAgentDetails(initialSelectedAgentId);
      onAgentSelected?.();
    }
  }, [initialSelectedAgentId, agents]);

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
      const [agentDetails, memory, messages] = await Promise.allSettled([
        api.getAgent(agentId),
        api.getCoreMemory(agentId),
        api.getAgentMessages(agentId, 20),
      ]);

      setAgents(prevAgents =>
        prevAgents.map(agent =>
          agent.id === agentId
            ? {
                ...agent,
                ...(agentDetails.status === 'fulfilled' ? agentDetails.value : {}),
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

  async function handleRename(agentId: string, newName: string) {
    if (!newName.trim()) return;

    try {
      await api.updateAgent(agentId, { name: newName });
      setAgents(prevAgents =>
        prevAgents.map(agent =>
          agent.id === agentId ? { ...agent, name: newName } : agent
        )
      );
      setEditingAgent(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to rename agent');
    }
  }

  async function handleDelete(agentId: string) {
    try {
      await api.deleteAgent(agentId);
      setAgents(prevAgents => prevAgents.filter(agent => agent.id !== agentId));
      if (expandedAgent === agentId) {
        setExpandedAgent(null);
      }
      setDeleteConfirm(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete agent');
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

      <div style={{ display: 'grid', gridTemplateColumns: expandedAgent ? '400px 1fr' : '1fr', gap: '1.5rem' }}>
        {/* Agent list */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.01)',
          border: '1px solid var(--border-subtle)',
          overflow: 'hidden',
        }}>
          {agents.map((agent, index) => {
            const isSelected = expandedAgent === agent.id;
            const isLoading = loadingDetails === agent.id;

            return (
              <div
                key={agent.id}
                style={{
                  padding: '1rem 1.5rem',
                  background: isSelected ? 'rgba(0, 255, 136, 0.08)' : 'transparent',
                  borderBottom: index < agents.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                  borderLeft: isSelected ? '3px solid var(--neon-green)' : '3px solid transparent',
                  transition: 'all 0.2s ease',
                }}
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
                <div className="flex items-center justify-between">
                  <div style={{ flex: 1, minWidth: 0 }} onClick={() => !isLoading && loadAgentDetails(agent.id)}>
                    <div style={{
                      fontSize: '0.9375rem',
                      fontWeight: 600,
                      color: isSelected ? 'var(--neon-green)' : 'var(--text-primary)',
                      marginBottom: '0.25rem',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {agent.name}
                    </div>
                    <div className="flex items-center gap-2 text-small" style={{ color: 'var(--text-tertiary)' }}>
                      <span className="font-mono">{agent.model}</span>
                      <span>•</span>
                      <span>{agent.agent_type}</span>
                    </div>
                  </div>
                  {isLoading ? (
                    <div className="text-small text-muted">Loading...</div>
                  ) : (
                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => setEditingAgent({ id: agent.id, name: agent.name })}
                        className="btn-secondary"
                        title="Rename agent"
                        style={{
                          padding: '0.375rem 0.75rem',
                          fontSize: '0.75rem',
                          fontWeight: 500,
                          textTransform: 'uppercase',
                          letterSpacing: '0.05em',
                        }}
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(agent.id)}
                        className="btn-secondary"
                        title="Delete agent"
                        style={{
                          padding: '0.375rem 0.75rem',
                          fontSize: '0.75rem',
                          fontWeight: 500,
                          textTransform: 'uppercase',
                          letterSpacing: '0.05em',
                          color: 'var(--error)',
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  )}
                </div>
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
                      <div key={tool.id || tool.name || idx} style={{
                        padding: '0.75rem',
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid var(--border-subtle)',
                      }}>
                        <div className="font-mono text-small" style={{ color: 'var(--neon-magenta)' }}>
                          {tool.name || tool}
                        </div>
                        {tool.description && (
                          <div className="text-small" style={{ color: 'var(--text-tertiary)', marginTop: '0.25rem' }}>
                            {tool.description}
                          </div>
                        )}
                        {tool.tags && tool.tags.length > 0 && (
                          <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.25rem' }}>
                            {tool.tags.map((tag: string) => (
                              <span key={tag} className="badge badge-neutral" style={{ fontSize: '0.625rem' }}>
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* System Prompt */}
              {agent.system && (
                <div style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
                  <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem' }}>
                    System Prompt
                  </h4>
                  <div style={{
                    padding: '1rem',
                    background: 'rgba(0, 0, 0, 0.3)',
                    border: '1px solid var(--border-subtle)',
                    maxHeight: '300px',
                    overflow: 'auto',
                  }}>
                    <pre style={{
                      color: 'var(--text-secondary)',
                      fontSize: '0.8125rem',
                      lineHeight: '1.7',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      margin: 0,
                    }}>
                      {agent.system}
                    </pre>
                  </div>
                </div>
              )}

              {/* LLM Config */}
              {agent.llm_config && (
                <div style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
                  <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem' }}>
                    LLM Configuration
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
                    {agent.llm_config.model && (
                      <div>
                        <div className="text-small text-muted">Model</div>
                        <div className="font-mono text-small" style={{ color: 'var(--text-secondary)' }}>
                          {agent.llm_config.model}
                        </div>
                      </div>
                    )}
                    {agent.llm_config.context_window && (
                      <div>
                        <div className="text-small text-muted">Context Window</div>
                        <div className="font-mono text-small" style={{ color: 'var(--text-secondary)' }}>
                          {agent.llm_config.context_window.toLocaleString()}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Embedding Config */}
              {agent.embedding_config && (
                <div style={{ marginBottom: '1.5rem', paddingBottom: '1.5rem', borderBottom: '1px solid var(--border-subtle)' }}>
                  <h4 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '1rem' }}>
                    Embedding Configuration
                  </h4>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.75rem' }}>
                    {agent.embedding_config.embedding_model && (
                      <div>
                        <div className="text-small text-muted">Model</div>
                        <div className="font-mono text-small" style={{ color: 'var(--text-secondary)' }}>
                          {agent.embedding_config.embedding_model}
                        </div>
                      </div>
                    )}
                    {agent.embedding_config.embedding_dim && (
                      <div>
                        <div className="text-small text-muted">Dimensions</div>
                        <div className="font-mono text-small" style={{ color: 'var(--text-secondary)' }}>
                          {agent.embedding_config.embedding_dim}
                        </div>
                      </div>
                    )}
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

      {/* Rename Modal */}
      {editingAgent && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }} onClick={() => setEditingAgent(null)}>
          <div className="card" style={{
            maxWidth: '400px',
            width: '100%',
            margin: '1rem',
          }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginBottom: '1rem', fontSize: '1.25rem', fontWeight: 600 }}>Rename Agent</h3>
            <form onSubmit={(e) => {
              e.preventDefault();
              const formData = new FormData(e.currentTarget);
              const newName = formData.get('name') as string;
              handleRename(editingAgent.id, newName);
            }}>
              <input
                type="text"
                name="name"
                defaultValue={editingAgent.name}
                className="input"
                style={{ width: '100%', marginBottom: '1rem' }}
                autoFocus
              />
              <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => setEditingAgent(null)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Rename
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }} onClick={() => setDeleteConfirm(null)}>
          <div className="card" style={{
            maxWidth: '400px',
            width: '100%',
            margin: '1rem',
            background: 'rgba(255, 0, 100, 0.05)',
            borderColor: 'var(--neon-magenta)',
          }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginBottom: '1rem', fontSize: '1.25rem', fontWeight: 600, color: 'var(--neon-magenta)' }}>
              Delete Agent?
            </h3>
            <p style={{ marginBottom: '1.5rem', color: 'var(--text-secondary)' }}>
              Are you sure you want to delete "{agents.find(a => a.id === deleteConfirm)?.name}"? This action cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setDeleteConfirm(null)}
                className="btn btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={() => handleDelete(deleteConfirm)}
                className="btn"
                style={{
                  background: 'var(--neon-magenta)',
                  color: 'var(--bg-primary)',
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
