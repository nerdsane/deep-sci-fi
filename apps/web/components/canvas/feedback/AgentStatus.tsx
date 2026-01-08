/**
 * AgentStatus - Enhanced agent activity indicator
 */
import React from 'react';

export interface AgentStatusProps {
  isThinking: boolean;
  action?: string;
  progress?: number;
  onCancel?: () => void;
}

export function AgentStatus({ isThinking, action, progress, onCancel }: AgentStatusProps) {
  if (!isThinking) return null;

  return (
    <div className="dsf-agent-status">
      <div className="dsf-agent-status__dot" />
      <div className="dsf-agent-status__content">
        <span className="dsf-agent-status__label">
          {action || 'Agent thinking...'}
        </span>
        {progress !== undefined && progress >= 0 && (
          <div className="dsf-agent-status__progress">
            <div
              className="dsf-agent-status__progress-bar"
              style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
            />
          </div>
        )}
      </div>
      {onCancel && (
        <button className="dsf-agent-status__cancel" onClick={onCancel}>
          Cancel
        </button>
      )}
    </div>
  );
}
