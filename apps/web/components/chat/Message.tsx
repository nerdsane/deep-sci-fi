'use client';

import type { MessageType } from './ChatPanel';
import { MessageAction } from './MessageAction';

interface MessageProps {
  message: MessageType;
}

export function Message({ message }: MessageProps) {
  const isAgent = message.role === 'agent';
  const isSystem = message.role === 'system';

  if (isSystem) {
    return (
      <div className="message message--system">
        <div className="message__content">
          <p className="message__text">{message.content}</p>
          <span className="message__timestamp">
            {formatTime(message.timestamp)}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={`message ${isAgent ? 'message--agent' : 'message--user'}`}>
      {isAgent && (
        <div className="message__avatar">
          <AgentIcon />
        </div>
      )}

      <div className="message__content">
        {message.type === 'text' && (
          <p className="message__text">{message.content}</p>
        )}

        {message.type === 'action' && (
          <MessageAction action={message.action} data={message.data} />
        )}

        <span className="message__timestamp">
          {formatTime(message.timestamp)}
        </span>
      </div>

      {!isAgent && (
        <div className="message__avatar">
          <UserAvatar />
        </div>
      )}
    </div>
  );
}

function AgentIcon() {
  return (
    <div className="avatar avatar--agent">
      <span className="avatar__icon">🤖</span>
    </div>
  );
}

function UserAvatar() {
  return (
    <div className="avatar avatar--user">
      <span className="avatar__icon">👤</span>
    </div>
  );
}

function formatTime(date: Date): string {
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);

  if (seconds < 60) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;

  return date.toLocaleDateString();
}
