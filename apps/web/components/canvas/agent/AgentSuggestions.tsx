/**
 * AgentSuggestions - Proactive suggestions from the agent
 *
 * Shows suggestions sent by the agent via send_suggestion tool.
 * Only displays real agent suggestions - no static fallback patterns.
 */
import React, { useState, useEffect } from 'react';
import type { World, Story } from '@/types/dsf';

export interface Suggestion {
  id: string;
  type?: 'rule' | 'branch' | 'character' | 'continuation' | 'world' | 'custom';
  title: string;
  description: string; // Full text, never truncated
  action: string;
  priority: 'high' | 'medium' | 'low';
  data?: any;
}

// Agent suggestion from Agent Bus
export interface AgentSuggestion {
  id: string;
  priority: 'high' | 'medium' | 'low';
  title: string;
  description: string;
  actionId: string;
  actionLabel?: string;
  actionData?: any;
}

export interface AgentSuggestionsProps {
  world?: World | null;
  story?: Story | null;
  stories?: Story[];
  /** Suggestions from agent (via Agent Bus) - these take priority */
  agentSuggestions?: AgentSuggestion[];
  onAccept: (suggestion: Suggestion) => void;
  onDismiss: (suggestionId: string) => void;
  maxSuggestions?: number;
  position?: 'sidebar' | 'floating' | 'inline';
}

export function AgentSuggestions({
  world,
  story,
  stories = [],
  agentSuggestions = [],
  onAccept,
  onDismiss,
  maxSuggestions = 5,
  position = 'floating',
}: AgentSuggestionsProps) {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  // Only show real agent suggestions - no static fallback patterns
  useEffect(() => {
    // Convert agent suggestions to Suggestion format
    const fromAgent: Suggestion[] = agentSuggestions.map((s) => ({
      id: s.id,
      type: 'custom' as const,
      title: s.title,
      description: s.description,
      action: s.actionLabel || 'Accept',
      priority: s.priority,
      data: { actionId: s.actionId, ...s.actionData },
    }));

    // Filter, sort, and limit
    const filtered = fromAgent
      .filter((s) => !dismissedIds.has(s.id))
      .sort((a, b) => {
        const priorityOrder = { high: 0, medium: 1, low: 2 };
        return priorityOrder[a.priority] - priorityOrder[b.priority];
      })
      .slice(0, maxSuggestions);

    setSuggestions(filtered);
  }, [agentSuggestions, dismissedIds, maxSuggestions]);

  const handleDismiss = (id: string) => {
    setDismissedIds((prev) => new Set([...prev, id]));
    onDismiss(id);
  };

  if (suggestions.length === 0) return null;

  return (
    <div className={`dsf-agent-suggestions dsf-agent-suggestions--${position} ${isCollapsed ? 'dsf-agent-suggestions--collapsed' : ''}`}>
      <button
        className="dsf-agent-suggestions__header"
        onClick={() => setIsCollapsed(!isCollapsed)}
      >
        <span className="dsf-agent-suggestions__icon">◇</span>
        <span className="dsf-agent-suggestions__title">
          Agent Suggests ({suggestions.length})
        </span>
        <span className="dsf-agent-suggestions__toggle">
          {isCollapsed ? '▼' : '▲'}
        </span>
      </button>

      {!isCollapsed && (
        <div className="dsf-agent-suggestions__list">
          {suggestions.map((suggestion) => (
            <div
              key={suggestion.id}
              className={`dsf-agent-suggestions__item dsf-agent-suggestions__item--${suggestion.priority}`}
            >
              <div className="dsf-agent-suggestions__item-header">
                <span className="dsf-agent-suggestions__item-type">
                  {suggestion.type === 'rule' && '◈'}
                  {suggestion.type === 'branch' && '◇'}
                  {suggestion.type === 'character' && '○'}
                  {suggestion.type === 'continuation' && '→'}
                  {suggestion.type === 'world' && '✦'}
                  {suggestion.type === 'custom' && '◆'}
                </span>
                <span className="dsf-agent-suggestions__item-title">
                  {suggestion.title}
                </span>
                <button
                  className="dsf-agent-suggestions__dismiss"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDismiss(suggestion.id);
                  }}
                >
                  ×
                </button>
              </div>
              <p className="dsf-agent-suggestions__item-desc">{suggestion.description}</p>
              <button
                className="dsf-agent-suggestions__action"
                onClick={() => onAccept(suggestion)}
              >
                {suggestion.action} →
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
