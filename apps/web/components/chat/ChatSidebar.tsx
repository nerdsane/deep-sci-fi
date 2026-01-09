'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import type { UnifiedWSClient, StreamChunk, HistoryMessage } from '@/lib/unified-ws-client';

/**
 * Message types for terminal-style rendering
 */
type MessageType = 'user' | 'agent' | 'reasoning' | 'tool_call' | 'tool_result' | 'error' | 'warning' | 'info' | 'system';

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
  wsClient: UnifiedWSClient | null;
  onAgentTypeChange?: (agentType: 'user' | 'world', worldName?: string) => void;
  agentType?: 'user' | 'world' | null;
  agentWorldName?: string | null;
}

export function ChatSidebar({ wsClient, onAgentTypeChange, agentType, agentWorldName }: ChatSidebarProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Track streaming message IDs
  const reasoningIdRef = useRef<string | null>(null);
  const assistantIdRef = useRef<string | null>(null);
  const toolCallIdsRef = useRef<Map<string, string>>(new Map());

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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

  /**
   * Handle incoming chat chunks from WebSocket
   */
  const handleChatChunk = useCallback((chunk: StreamChunk) => {
    switch (chunk.type) {
      case 'reasoning':
        if (!reasoningIdRef.current) {
          reasoningIdRef.current = `reasoning-${Date.now()}`;
          upsertMessage(reasoningIdRef.current, {
            type: 'reasoning',
            content: chunk.content || '',
            isStreaming: true,
          });
        } else {
          appendToMessage(reasoningIdRef.current, chunk.content || '');
        }
        break;

      case 'reasoning_end':
        if (reasoningIdRef.current) {
          upsertMessage(reasoningIdRef.current, { type: 'reasoning', isStreaming: false });
        }
        break;

      case 'assistant':
        if (!assistantIdRef.current) {
          assistantIdRef.current = `assistant-${Date.now()}`;
          upsertMessage(assistantIdRef.current, {
            type: 'agent',
            content: chunk.content || '',
            isStreaming: true,
          });
        } else {
          appendToMessage(assistantIdRef.current, chunk.content || '');
        }
        break;

      case 'assistant_end':
        if (assistantIdRef.current) {
          upsertMessage(assistantIdRef.current, { type: 'agent', isStreaming: false });
        }
        break;

      case 'tool_call': {
        const tcId = chunk.toolCallId || `tc-${Date.now()}`;
        let msgId = toolCallIdsRef.current.get(tcId);
        if (!msgId) {
          msgId = `tool-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
          toolCallIdsRef.current.set(tcId, msgId);
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
        const msgId = tcId ? toolCallIdsRef.current.get(tcId) : null;
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
        setIsLoading(false);
        break;

      case 'warning':
        upsertMessage(`warning-${Date.now()}`, {
          type: 'warning',
          content: chunk.content || 'Warning',
        });
        break;

      case 'info': {
        const content = chunk.content || '';
        // Check for agent_type info (format: "agent_type:user" or "agent_type:world:WorldName")
        if (content.startsWith('agent_type:')) {
          const parts = content.split(':');
          const agentType = parts[1] as 'user' | 'world';
          const worldName = parts[2];
          onAgentTypeChange?.(agentType, worldName);
          // Don't display agent_type as a message
        } else {
          upsertMessage(`info-${Date.now()}`, {
            type: 'info',
            content,
          });
        }
        break;
      }

      case 'done':
        // Mark all streaming messages as complete
        if (reasoningIdRef.current) {
          upsertMessage(reasoningIdRef.current, { type: 'reasoning', isStreaming: false });
        }
        if (assistantIdRef.current) {
          upsertMessage(assistantIdRef.current, { type: 'agent', isStreaming: false });
        }
        // Reset refs for next message
        reasoningIdRef.current = null;
        assistantIdRef.current = null;
        toolCallIdsRef.current.clear();
        setIsLoading(false);
        break;
    }
  }, [upsertMessage, appendToMessage]);

  // Set up WebSocket chat chunk handler
  useEffect(() => {
    if (!wsClient) return;

    // Store the original handler to restore later
    const originalHandler = wsClient.onChatChunk;

    // Set our handler
    wsClient.onChatChunk = handleChatChunk;

    return () => {
      // Restore original handler on cleanup
      wsClient.onChatChunk = originalHandler;
    };
  }, [wsClient, handleChatChunk]);

  // Set up WebSocket message history handler
  useEffect(() => {
    if (!wsClient) return;

    const originalHistoryHandler = wsClient.onMessageHistory;

    wsClient.onMessageHistory = (history: HistoryMessage[]) => {
      if (history.length === 0) return;

      const mappedMessages: Message[] = history.map((msg) => ({
        id: msg.id,
        type: msg.messageType as MessageType,
        content: msg.content,
        timestamp: new Date(msg.createdAt),
        toolName: msg.toolName ?? undefined,
        toolArgs: msg.toolArgs ?? undefined,
        toolResult: msg.toolResult ?? undefined,
        toolStatus: msg.toolStatus as Message['toolStatus'],
      }));

      setMessages(mappedMessages);
    };

    return () => {
      wsClient.onMessageHistory = originalHistoryHandler;
    };
  }, [wsClient]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isLoading || !wsClient) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Reset streaming refs
    reasoningIdRef.current = null;
    assistantIdRef.current = null;
    toolCallIdsRef.current.clear();

    // Send message via WebSocket
    wsClient.sendChatMessage(userMessage.content);
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

      case 'warning':
        return (
          <div className="terminal-line terminal-warning">
            <span className="terminal-icon">⚠</span>
            <span className="terminal-content">{message.content}</span>
          </div>
        );

      case 'info':
        return (
          <div className="terminal-line terminal-info">
            <span className="terminal-icon">ℹ</span>
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

  const isConnected = wsClient?.isConnected() ?? false;

  // Compute header title based on connection state and agent type
  const getAgentTitle = () => {
    if (!isConnected) return 'Connecting...';
    if (!agentType) return 'Connected';
    if (agentType === 'user') return 'User Agent';
    if (agentType === 'world' && agentWorldName) return `World Agent: ${agentWorldName}`;
    return 'World Agent';
  };

  return (
    <aside className="chat-sidebar terminal-container">
      {/* Header with agent type indicator */}
      <div className="terminal-header">
        <div className="terminal-header-title">
          <span className={`terminal-status-dot ${isConnected ? 'connected' : 'disconnected'}`} />
          <span>{getAgentTitle()}</span>
        </div>
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
            placeholder={isConnected ? "Enter command..." : "Connecting..."}
            rows={1}
            disabled={isLoading || !isConnected}
          />
          <button
            type="submit"
            className="terminal-submit"
            disabled={!input.trim() || isLoading || !isConnected}
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
