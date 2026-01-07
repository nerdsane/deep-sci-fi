import React from 'react';
import './experience.css';

export interface ActionItem {
  id: string;
  label: string;
  description?: string;
  icon?: string;
  variant?: 'primary' | 'secondary' | 'branch';
}

export interface ActionBarProps {
  actions: ActionItem[];
  title?: string;
  onAction: (actionId: string) => void;
}

export function ActionBar({ actions, title, onAction }: ActionBarProps) {
  if (!actions || actions.length === 0) return null;

  const primaryActions = actions.filter(a => a.variant === 'primary' || !a.variant);
  const branchActions = actions.filter(a => a.variant === 'branch');

  return (
    <div className="exp-actions">
      <div className="exp-actions__glow" />

      {title && (
        <div className="exp-actions__header">
          <span className="exp-actions__ornament">✦</span>
          <span className="exp-actions__title">{title}</span>
          <span className="exp-actions__ornament">✦</span>
        </div>
      )}

      <div className="exp-actions__container">
        {primaryActions.map((action, i) => (
          <button
            key={action.id}
            className="exp-actions__btn exp-actions__btn--primary"
            onClick={() => onAction(action.id)}
            style={{ animationDelay: `${i * 100}ms` }}
          >
            <span className="exp-actions__btn-icon">
              {action.icon || '→'}
            </span>
            <span className="exp-actions__btn-text">{action.label}</span>
            <span className="exp-actions__btn-arrow">→</span>
          </button>
        ))}

        {branchActions.length > 0 && (
          <div className="exp-actions__branches">
            <span className="exp-actions__branches-label">Or explore:</span>
            {branchActions.map((action, i) => (
              <button
                key={action.id}
                className="exp-actions__btn exp-actions__btn--branch"
                onClick={() => onAction(action.id)}
                style={{ animationDelay: `${(primaryActions.length + i) * 100}ms` }}
              >
                <span className="exp-actions__btn-icon">◇</span>
                <div className="exp-actions__btn-content">
                  <span className="exp-actions__btn-text">{action.label}</span>
                  {action.description && (
                    <span className="exp-actions__btn-desc">{action.description}</span>
                  )}
                </div>
                <span className="exp-actions__btn-arrow">→</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
