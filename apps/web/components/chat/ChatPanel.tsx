'use client';

import { useState, useEffect, useRef } from 'react';
import { Message } from './Message';
import { ChatInput } from './ChatInput';
import { ChatHeader } from './ChatHeader';
import './chat.css';

export type ChatContext = {
  type: 'world' | 'story';
  worldId?: string;
  storyId?: string;
  view?: string;
};

export type MessageType = {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: Date;
  type?: 'text' | 'action';
  action?: any;
  data?: any;
};

export type AgentStatus = 'idle' | 'thinking' | 'error';

export type ViewMode = 'canvas' | 'visual-novel' | 'fullscreen' | 'reading';

interface ChatPanelProps {
  worldId?: string;
  storyId?: string;
  messages: MessageType[];
  onSendMessage: (message: string, context: ChatContext) => Promise<void>;
  agentStatus: AgentStatus;
  viewMode: ViewMode;
  isMobile: boolean;
}

export function ChatPanel({
  worldId,
  storyId,
  messages,
  onSendMessage,
  agentStatus,
  viewMode = 'canvas',
  isMobile = false,
}: ChatPanelProps) {
  const [isOpen, setIsOpen] = useState(!isMobile);
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Determine context
  const context: ChatContext = {
    type: storyId ? 'story' : 'world',
    worldId,
    storyId,
    view: viewMode,
  };

  const handleSend = async () => {
    if (!input.trim() || agentStatus === 'thinking') return;
    await onSendMessage(input, context);
    setInput('');
  };

  // Adaptive behavior based on view mode
  const chatBehavior = getChatBehavior(viewMode, isMobile);

  if (chatBehavior === 'hidden') {
    return null;
  }

  if (chatBehavior === 'minimized-floating' || chatBehavior === 'floating-bubble') {
    return (
      <button
        className="chat-bubble"
        onClick={() => setIsOpen(true)}
        aria-label="Open chat"
      >
        <span className="chat-bubble__icon">💬</span>
        {messages.filter(m => m.role === 'agent').length > 0 && (
          <span className="chat-bubble__badge">
            {messages.filter(m => m.role === 'agent').length}
          </span>
        )}
      </button>
    );
  }

  const panelClassName = `chat-panel chat-panel--${chatBehavior} ${
    isOpen ? 'chat-panel--open' : ''
  } ${isMobile ? 'chat-panel--mobile' : 'chat-panel--desktop'}`;

  return (
    <aside className={panelClassName}>
      {isMobile && (
        <div
          className="chat-panel__handle"
          onTouchStart={(e) => {
            // Touch gesture handling for mobile drawer
          }}
        />
      )}

      <ChatHeader
        context={context}
        onCollapse={() => setIsOpen(false)}
        onClose={() => setIsOpen(false)}
      />

      <div className="message-list">
        {messages.map((message) => (
          <Message
            key={message.id}
            role={message.role}
            content={message.content}
            timestamp={message.timestamp}
            type={message.type}
            action={message.action}
            data={message.data}
          />
        ))}

        {agentStatus === 'thinking' && (
          <div className="agent-status">
            <div className="agent-status__dots">
              <span className="agent-status__dot" />
              <span className="agent-status__dot" />
              <span className="agent-status__dot" />
            </div>
            <span className="agent-status__text">Agent thinking...</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <ChatInput
        value={input}
        onChange={setInput}
        onSend={handleSend}
        disabled={agentStatus === 'thinking'}
        placeholder="Message the agent..."
      />
    </aside>
  );
}

/**
 * Determine chat panel behavior based on view mode
 */
function getChatBehavior(
  viewMode: ViewMode,
  isMobile: boolean
): string {
  const behaviors = {
    canvas: {
      desktop: 'persistent-sidebar',
      mobile: 'bottom-drawer',
    },
    'visual-novel': {
      desktop: 'minimized-floating',
      mobile: 'hidden',
    },
    fullscreen: {
      desktop: 'hidden',
      mobile: 'hidden',
    },
    reading: {
      desktop: 'minimal-sidebar',
      mobile: 'floating-bubble',
    },
  };

  return behaviors[viewMode]?.[isMobile ? 'mobile' : 'desktop'] || 'persistent-sidebar';
}
