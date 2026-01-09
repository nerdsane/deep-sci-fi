'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';

/**
 * Message types for terminal-style rendering
 */
type MessageType = 'user' | 'agent' | 'reasoning' | 'tool_call' | 'tool_result' | 'error' | 'system';

interface Message {
  id: string;
  type: MessageType;
  content: string;
  timestamp: Date;
  // Tool-specific fields
  toolName?: string;
  toolArgs?: string;
  toolResult?: string;
  toolStatus?: 'pending' | 'running' | 'success' | 'error';
  // For streaming accumulation
  isStreaming?: boolean;
}

interface ChatSidebarProps {
  onSendMessage: (message: string) => void;
}

/**
 * Parse SSE stream and yield chunks
 */
async function* parseSSEStream(response: Response): AsyncGenerator<any> {
  const reader = response.body?.getReader();
  if (!reader) return;

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6).trim();
          if (data === '[DONE]') return;
          try {
            yield JSON.parse(data);
          } catch {
            // Skip malformed JSON
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export function ChatSidebar({ onSendMessage }: ChatSidebarProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      type: 'system',
      content: 'Deep Sci-Fi Agent Ready',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Check connection status on mount
  useEffect(() => {
    checkConnection();
  }, []);

  async function checkConnection() {
    try {
      const res = await fetch('/api/health');
      setIsConnected(res.ok);
    } catch {
      setIsConnected(false);
    }
  }

  /**
   * Add or update a message by ID
   */
  const upsertMessage = useCallback((id: string, update: Partial<Message> & { type: MessageType }) => {
    setMessages(prev => {
      const idx = prev.findIndex(m => m.id === id);
      if (idx >= 0) {
        // Update existing
        const updated = [...prev];
        updated[idx] = { ...updated[idx], ...update };
        return updated;
      } else {
        // Add new
        return [...prev, {
          id,
          content: '',
          timestamp: new Date(),
          ...update,
        }];
      }
    });
  }, []);

  /**
   * Append content to a message
   */
  const appendToMessage = useCallback((id: string, content: string) => {
    setMessages(prev => {
      const idx = prev.findIndex(m => m.id === id);
      if (idx >= 0) {
        const updated = [...prev];
        updated[idx] = {
          ...updated[idx],
          content: updated[idx].content + content,
        };
        return updated;
      }
      return prev;
    });
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Call the parent handler
    onSendMessage(userMessage.content);

    // Abort any existing stream
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();

    // Track streaming message IDs
    let reasoningId: string | null = null;
    let assistantId: string | null = null;
    const toolCallIds = new Map<string, string>(); // toolCallId -> messageId

    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage.content }),
        signal: abortControllerRef.current.signal,
      });

      if (!res.ok) {
        const error = await res.json().catch(() => ({ error: 'Unknown error' }));
        upsertMessage(`error-${Date.now()}`, {
          type: 'error',
          content: error.error || 'Failed to connect to agent',
        });
        setIsLoading(false);
        return;
      }

      // Process SSE stream
      for await (const chunk of parseSSEStream(res)) {
        switch (chunk.type) {
          case 'reasoning':
            if (!reasoningId) {
              reasoningId = `reasoning-${Date.now()}`;
              upsertMessage(reasoningId, {
                type: 'reasoning',
                content: chunk.content || '',
                isStreaming: true,
              });
            } else {
              appendToMessage(reasoningId, chunk.content || '');
            }
            break;

          case 'reasoning_end':
            if (reasoningId) {
              upsertMessage(reasoningId, { type: 'reasoning', isStreaming: false });
            }
            break;

          case 'assistant':
            if (!assistantId) {
              assistantId = `assistant-${Date.now()}`;
              upsertMessage(assistantId, {
                type: 'agent',
                content: chunk.content || '',
                isStreaming: true,
              });
            } else {
              appendToMessage(assistantId, chunk.content || '');
            }
            break;

          case 'assistant_end':
            if (assistantId) {
              upsertMessage(assistantId, { type: 'agent', isStreaming: false });
            }
            break;

          case 'tool_call': {
            const tcId = chunk.toolCallId || `tc-${Date.now()}`;
            let msgId = toolCallIds.get(tcId);
            if (!msgId) {
              msgId = `tool-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
              toolCallIds.set(tcId, msgId);
            }
            upsertMessage(msgId, {
              type: 'tool_call',
              content: '',
              toolName: chunk.toolName,
              toolArgs: chunk.toolArgs,
              toolStatus: chunk.toolStatus || 'pending',
            });
            break;
          }

          case 'tool_result': {
            const tcId = chunk.toolCallId;
            const msgId = tcId ? toolCallIds.get(tcId) : null;
            if (msgId) {
              upsertMessage(msgId, {
                type: 'tool_call',
                toolResult: chunk.toolResult,
                toolStatus: chunk.toolStatus || 'success',
              });
            } else {
              // Standalone result
              upsertMessage(`result-${Date.now()}`, {
                type: 'tool_result',
                content: chunk.toolResult || '',
                toolName: chunk.toolName,
                toolStatus: chunk.toolStatus || 'success',
              });
            }
            break;
          }

          case 'error':
            upsertMessage(`error-${Date.now()}`, {
              type: 'error',
              content: chunk.content || 'Unknown error',
            });
            break;

          case 'done':
            // Mark all streaming messages as complete
            if (reasoningId) {
              upsertMessage(reasoningId, { type: 'reasoning', isStreaming: false });
            }
            if (assistantId) {
              upsertMessage(assistantId, { type: 'agent', isStreaming: false });
            }
            break;
        }
      }
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        console.error('Chat stream error:', error);
        upsertMessage(`error-${Date.now()}`, {
          type: 'error',
          content: 'Connection error. Please check if all services are running.',
        });
      }
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  /**
   * Render a message based on its type
   */
  function renderMessage(message: Message) {
    switch (message.type) {
      case 'user':
        return (
          <div className="terminal-line terminal-user">
            <span className="terminal-prompt">&gt;</span>
            <span className="terminal-content">{message.content}</span>
          </div>
        );

      case 'reasoning':
        return (
          <div className="terminal-line terminal-reasoning">
            <span className="terminal-icon">✻</span>
            <span className="terminal-label">Thinking...</span>
            {message.content && (
              <div className="terminal-reasoning-content">
                {message.content}
              </div>
            )}
            {message.isStreaming && <span className="terminal-cursor">▊</span>}
          </div>
        );

      case 'tool_call':
        return (
          <div className="terminal-line terminal-tool">
            <span className={`terminal-dot terminal-dot--${message.toolStatus}`}>●</span>
            <span className="terminal-tool-name">{message.toolName}</span>
            {message.toolArgs && (
              <span className="terminal-tool-args">
                ({formatToolArgs(message.toolArgs)})
              </span>
            )}
            {message.toolResult && (
              <div className="terminal-tool-result">
                <span className="terminal-result-prefix">⎿</span>
                <span className="terminal-result-content">
                  {formatToolResult(message.toolResult)}
                </span>
              </div>
            )}
          </div>
        );

      case 'tool_result':
        return (
          <div className="terminal-line terminal-result">
            <span className="terminal-result-prefix">⎿</span>
            <span className="terminal-result-content">
              {formatToolResult(message.content)}
            </span>
          </div>
        );

      case 'agent':
        return (
          <div className="terminal-line terminal-agent">
            <span className="terminal-content">{message.content}</span>
            {message.isStreaming && <span className="terminal-cursor">▊</span>}
          </div>
        );

      case 'error':
        return (
          <div className="terminal-line terminal-error">
            <span className="terminal-icon">✖</span>
            <span className="terminal-content">{message.content}</span>
          </div>
        );

      case 'system':
        return (
          <div className="terminal-line terminal-system">
            <span className="terminal-content">{message.content}</span>
          </div>
        );

      default:
        return (
          <div className="terminal-line">
            <span className="terminal-content">{message.content}</span>
          </div>
        );
    }
  }

  return (
    <aside className="chat-sidebar terminal-container">
      <div className="terminal-header">
        <div className={`terminal-status ${isConnected ? 'terminal-status--connected' : ''}`} />
        <span className="terminal-title">Agent Terminal</span>
      </div>

      <div className="terminal-output">
        {messages.map((message) => (
          <div key={message.id} className="terminal-message">
            {renderMessage(message)}
          </div>
        ))}
        {isLoading && messages[messages.length - 1]?.type === 'user' && (
          <div className="terminal-line terminal-loading">
            <span className="terminal-spinner">◐</span>
            <span className="terminal-content">Processing...</span>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="terminal-input-container">
        <form className="terminal-form" onSubmit={handleSubmit}>
          <span className="terminal-input-prompt">&gt;</span>
          <textarea
            className="terminal-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Enter command..."
            rows={1}
            disabled={isLoading}
          />
          <button
            type="submit"
            className="terminal-submit"
            disabled={!input.trim() || isLoading}
          >
            ↵
          </button>
        </form>
      </div>
    </aside>
  );
}

/**
 * Format tool arguments for display
 */
function formatToolArgs(args: string): string {
  try {
    const parsed = JSON.parse(args);
    return Object.entries(parsed)
      .map(([k, v]) => `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`)
      .join(', ');
  } catch {
    return args.length > 100 ? args.slice(0, 100) + '...' : args;
  }
}

/**
 * Format tool result for display
 */
function formatToolResult(result: string): string {
  try {
    const parsed = JSON.parse(result);
    if (typeof parsed === 'object') {
      // Pretty print but truncate if too long
      const pretty = JSON.stringify(parsed, null, 2);
      return pretty.length > 500 ? pretty.slice(0, 500) + '...' : pretty;
    }
    return String(parsed);
  } catch {
    return result.length > 500 ? result.slice(0, 500) + '...' : result;
  }
}
