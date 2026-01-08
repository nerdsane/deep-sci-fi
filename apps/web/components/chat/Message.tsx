'use client';

import { MessageAction } from './MessageAction';

interface MessageProps {
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: Date;
  type?: 'text' | 'action';
  action?: any;
  data?: any;
}

export function Message({ role, content, timestamp, type = 'text', action, data }: MessageProps) {
  const isAgent = role === 'agent';
  const isSystem = role === 'system';

  if (isSystem) {
    return (
      <div className="message message--system">
        <div className="message__content">
          <p className="message__text">{content}</p>
          <span className="message__timestamp">
            {formatTime(timestamp)}
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
        {type === 'text' && (
          <p className="message__text">{content}</p>
        )}

        {type === 'action' && (
          <MessageAction action={action} data={data} />
        )}

        <span className="message__timestamp">
          {formatTime(timestamp)}
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
      ◇
    </div>
  );
}

function UserAvatar() {
  return (
    <div className="avatar avatar--user">
      ◈
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
