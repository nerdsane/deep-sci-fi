'use client';

import React, { useState, useRef, useEffect } from 'react';

interface Message {
  id: string;
  role: 'user' | 'agent';
  content: string;
  timestamp: Date;
}

interface ChatSidebarProps {
  onSendMessage: (message: string) => void;
}

export function ChatSidebar({ onSendMessage }: ChatSidebarProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'agent',
      content: 'Hello! I\'m your Deep Sci-Fi agent. I can help you create and explore scientifically-grounded science fiction worlds and stories. What would you like to do?',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // Call the parent handler
    onSendMessage(userMessage.content);

    try {
      // Send to API
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage.content }),
      });

      if (res.ok) {
        const data = await res.json();
        const agentMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'agent',
          content: data.response || 'I received your message. Let me work on that.',
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, agentMessage]);
      } else {
        // Add error message
        const agentMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'agent',
          content: 'I\'m having trouble connecting to the backend. Please make sure the Letta server is running.',
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, agentMessage]);
      }
    } catch (error) {
      console.error('Chat error:', error);
      const agentMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'agent',
        content: 'Connection error. Please check if all services are running.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, agentMessage]);
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

  return (
    <aside className="chat-sidebar">
      <div className="chat-header">
        <div className={`chat-header__status ${isConnected ? 'chat-header__status--connected' : ''}`} />
        <span className="chat-header__title">Agent Chat</span>
      </div>

      <div className="chat-messages">
        {messages.map((message) => (
          <div key={message.id} className={`chat-message chat-message--${message.role}`}>
            <div className="chat-message__role">
              {message.role === 'user' ? 'You' : 'Agent'}
            </div>
            <div className="chat-message__content">
              {message.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="chat-message chat-message--agent">
            <div className="chat-message__role">Agent</div>
            <div className="chat-message__content">
              <span style={{ opacity: 0.6 }}>Thinking...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <form className="chat-input-form" onSubmit={handleSubmit}>
          <textarea
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask the agent anything..."
            rows={1}
            disabled={isLoading}
          />
          <button
            type="submit"
            className="chat-send-btn"
            disabled={!input.trim() || isLoading}
          >
            Send
          </button>
        </form>
      </div>
    </aside>
  );
}
