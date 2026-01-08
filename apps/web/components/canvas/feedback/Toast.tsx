/**
 * Toast - DSF-styled notification system
 */
import React, { useEffect, useState } from 'react';
import { useFeedbackSafe } from '../context/FeedbackContext';

export interface ToastProps {
  id: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'agent';
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
  onDismiss: (id: string) => void;
}

export function Toast({ id, message, type, duration = 5000, action, onDismiss }: ToastProps) {
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        setIsExiting(true);
        setTimeout(() => onDismiss(id), 300);
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, id, onDismiss]);

  const handleDismiss = () => {
    setIsExiting(true);
    setTimeout(() => onDismiss(id), 300);
  };

  return (
    <div className={`dsf-toast dsf-toast--${type} ${isExiting ? 'dsf-toast--exiting' : ''}`}>
      <div className="dsf-toast__icon">
        {type === 'success' && '✓'}
        {type === 'info' && '◈'}
        {type === 'warning' && '!'}
        {type === 'agent' && '◇'}
      </div>
      <div className="dsf-toast__content">
        <p className="dsf-toast__message">{message}</p>
        {action && (
          <button
            className="dsf-toast__action"
            onClick={() => {
              action.onClick();
              handleDismiss();
            }}
          >
            {action.label}
          </button>
        )}
      </div>
      <button className="dsf-toast__close" onClick={handleDismiss}>
        ×
      </button>
    </div>
  );
}

export interface ToastContainerProps {
  toasts?: Array<Omit<ToastProps, 'onDismiss'>>;
  onDismiss?: (id: string) => void;
  position?: 'top-right' | 'bottom-right' | 'bottom-center';
}

/**
 * Toast container that can work in two modes:
 * 1. Self-contained: Uses FeedbackContext automatically (no props needed)
 * 2. Controlled: Pass toasts and onDismiss explicitly
 */
export function ToastContainer({ toasts: propToasts, onDismiss: propOnDismiss, position = 'bottom-right' }: ToastContainerProps) {
  const feedback = useFeedbackSafe();

  // Use props if provided, otherwise fall back to context
  const toasts = propToasts ?? feedback?.toasts ?? [];
  const onDismiss = propOnDismiss ?? feedback?.dismissToast ?? (() => {});

  if (toasts.length === 0) return null;

  return (
    <div className={`dsf-toast-container dsf-toast-container--${position}`}>
      {toasts.map((toast) => (
        <Toast key={toast.id} {...toast} onDismiss={onDismiss} />
      ))}
    </div>
  );
}
