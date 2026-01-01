import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  text?: string;
  content?: string;
  agent_id?: string;
  run_id?: string;
  created_at: string;
  tool_calls?: any[];
}

export function MessagesView() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');

  useEffect(() => {
    loadMessages();
  }, []);

  async function loadMessages() {
    try {
      setLoading(true);
      const response = await api.listMessages(100);
      setMessages(Array.isArray(response) ? response : response.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load messages');
    } finally {
      setLoading(false);
    }
  }

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!searchQuery.trim()) {
      loadMessages();
      return;
    }

    try {
      setLoading(true);
      const response = await api.searchMessages(searchQuery);
      setMessages(response.messages || response.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
    } finally {
      setLoading(false);
    }
  }

  const filteredMessages = roleFilter === 'all'
    ? messages
    : messages.filter(m => m.role === roleFilter);

  const roleColors: Record<string, string> = {
    user: 'color-teal',
    assistant: 'color-green',
    system: 'color-lemon',
    tool: 'color-magenta',
  };

  if (loading && messages.length === 0) {
    return <div className="loading">Loading messages...</div>;
  }

  return (
    <div>
      <div>
        <h2 className="section-title">Messages</h2>
        <p className="section-subtitle">
          Agent conversations and tool interactions
        </p>
      </div>

      {/* Stats */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value color-teal">{messages.length}</div>
          <div className="stat-label">Total Messages</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-teal">{messages.filter(m => m.role === 'user').length}</div>
          <div className="stat-label">User</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-green">{messages.filter(m => m.role === 'assistant').length}</div>
          <div className="stat-label">Assistant</div>
        </div>
        <div className="stat-card">
          <div className="stat-value color-magenta">{messages.filter(m => m.role === 'tool').length}</div>
          <div className="stat-label">Tool Calls</div>
        </div>
      </div>

      {/* Filters */}
      <div style={{ marginBottom: '1.5rem', display: 'flex', gap: '1rem', alignItems: 'center' }}>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          {['all', 'user', 'assistant', 'tool', 'system'].map((role) => (
            <button
              key={role}
              onClick={() => setRoleFilter(role)}
              className={`btn ${roleFilter === role ? 'btn-primary' : 'btn-secondary'}`}
              style={{ textTransform: 'capitalize' }}
            >
              {role}
            </button>
          ))}
        </div>
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="search-form">
        <div className="search-controls">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search messages..."
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
                loadMessages();
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

      {/* Message list */}
      <div className="card-list">
        {filteredMessages.map((message) => (
          <div key={message.id} className="card">
            <div className="flex justify-between items-start mb-3">
              <div style={{ flex: 1 }}>
                <div className="flex items-center gap-3 mb-2">
                  <span className={`badge badge-${message.role === 'user' ? 'neutral' : message.role === 'assistant' ? 'success' : 'failure'}`}>
                    {message.role}
                  </span>
                  {message.agent_id && (
                    <span className="text-small text-muted font-mono">
                      Agent: {message.agent_id.slice(0, 12)}
                    </span>
                  )}
                  {message.run_id && (
                    <span className="text-small text-muted font-mono">
                      Run: {message.run_id.slice(0, 12)}
                    </span>
                  )}
                </div>
                <div style={{
                  color: 'var(--text-primary)',
                  lineHeight: '1.7',
                  fontSize: '0.9375rem',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}>
                  {message.text || message.content || 'No content'}
                </div>
                {message.tool_calls && message.tool_calls.length > 0 && (
                  <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'rgba(255, 0, 255, 0.05)', border: '1px solid var(--border-subtle)' }}>
                    <div className="text-small text-muted mb-1">Tool Calls:</div>
                    {message.tool_calls.map((call: any, idx: number) => (
                      <div key={idx} className="font-mono text-small" style={{ color: 'var(--neon-magenta)' }}>
                        {call.function?.name || call.name || 'Unknown tool'}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }} className="text-small text-muted">
              {new Date(message.created_at).toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      {filteredMessages.length === 0 && !loading && (
        <div className="empty-state">No messages found</div>
      )}
    </div>
  );
}
