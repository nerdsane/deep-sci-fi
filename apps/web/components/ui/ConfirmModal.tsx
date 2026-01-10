import React from 'react';
import './confirm-modal.css';

export interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  message: string;
  warning?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'warning' | 'default';
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
}

export const ConfirmModal = React.memo(function ConfirmModal({
  isOpen,
  title,
  message,
  warning,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'default',
  onConfirm,
  onCancel,
  isLoading = false,
}: ConfirmModalProps) {
  // Handle escape key
  React.useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isLoading) {
        onCancel();
      }
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, isLoading, onCancel]);

  // Prevent body scroll when modal is open
  React.useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="confirm-modal__backdrop" onClick={isLoading ? undefined : onCancel}>
      <div
        className={`confirm-modal ${variant !== 'default' ? `confirm-modal--${variant}` : ''}`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-modal-title"
      >
        <div className="confirm-modal__icon">
          {variant === 'danger' ? '!' : variant === 'warning' ? '?' : 'i'}
        </div>

        <h2 id="confirm-modal-title" className="confirm-modal__title">
          {title}
        </h2>

        <p className="confirm-modal__message">{message}</p>

        {warning && (
          <div className="confirm-modal__warning">
            <span className="confirm-modal__warning-icon">!</span>
            {warning}
          </div>
        )}

        <div className="confirm-modal__actions">
          <button
            className="confirm-modal__button confirm-modal__button--cancel"
            onClick={onCancel}
            disabled={isLoading}
          >
            {cancelLabel}
          </button>
          <button
            className={`confirm-modal__button confirm-modal__button--confirm confirm-modal__button--${variant}`}
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? (
              <span className="confirm-modal__spinner" />
            ) : (
              confirmLabel
            )}
          </button>
        </div>
      </div>
    </div>
  );
});
