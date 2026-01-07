'use client';

import type { ChatContext } from './ChatPanel';

interface ChatHeaderProps {
  context: ChatContext;
  onCollapse: () => void;
  onClose: () => void;
}

export function ChatHeader({ context, onCollapse, onClose }: ChatHeaderProps) {
  const contextLabel = getContextLabel(context);

  return (
    <div className="chat-header">
      <div className="chat-header__context">
        <span className="chat-header__icon">◈</span>
        <span className="chat-header__label">{contextLabel}</span>
      </div>

      <div className="chat-header__actions">
        <button
          className="chat-header__button"
          onClick={onCollapse}
          aria-label="Minimize chat"
          title="Minimize"
        >
          ━
        </button>
        <button
          className="chat-header__button"
          onClick={onClose}
          aria-label="Close chat"
          title="Close"
        >
          ×
        </button>
      </div>
    </div>
  );
}

function getContextLabel(context: ChatContext): string {
  if (context.storyId) {
    return 'Story Agent';
  }
  if (context.worldId) {
    return 'World Agent';
  }
  return 'Canvas';
}
