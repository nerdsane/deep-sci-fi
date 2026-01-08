/**
 * FloatingInput - Context-aware input for talking to agent from anywhere
 *
 * Features:
 * - Cmd/Ctrl+K to open
 * - Context-aware: knows current view, selected element
 * - Types message to agent with context
 */
import React, { useState, useRef, useEffect, useCallback } from 'react';

export interface FloatingInputContext {
  view?: string;
  elementType?: string;
  elementId?: string;
  elementName?: string;
  selection?: string;
}

export interface FloatingInputProps {
  isVisible: boolean;
  onSend: (message: string, context: FloatingInputContext) => void;
  onClose: () => void;
  context?: FloatingInputContext;
  placeholder?: string;
}

export function FloatingInput({
  isVisible,
  onSend,
  onClose,
  context,
  placeholder = 'Ask the agent anything...',
}: FloatingInputProps) {
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input when visible
  useEffect(() => {
    if (isVisible && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isVisible]);

  // Handle escape to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isVisible) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isVisible, onClose]);

  const handleSubmit = useCallback((e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim()) {
      onSend(value.trim(), context || {});
      setValue('');
      onClose();
    }
  }, [value, context, onSend, onClose]);

  if (!isVisible) return null;

  const contextLabel = getContextLabel(context);

  return (
    <div className="dsf-floating-input-overlay" onClick={onClose}>
      <div className="dsf-floating-input" onClick={(e) => e.stopPropagation()}>
        {contextLabel && (
          <div className="dsf-floating-input__context">
            <span className="dsf-floating-input__context-icon">◈</span>
            {contextLabel}
          </div>
        )}
        <form className="dsf-floating-input__form" onSubmit={handleSubmit}>
          <input
            ref={inputRef}
            type="text"
            className="dsf-floating-input__input"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={placeholder}
            autoComplete="off"
          />
          <button
            type="submit"
            className="dsf-floating-input__send"
            disabled={!value.trim()}
          >
            Send
          </button>
        </form>
        <div className="dsf-floating-input__hints">
          <span className="dsf-floating-input__hint">
            <kbd>Enter</kbd> to send
          </span>
          <span className="dsf-floating-input__hint">
            <kbd>Esc</kbd> to close
          </span>
        </div>
      </div>
    </div>
  );
}

function getContextLabel(context?: FloatingInputContext): string | null {
  if (!context) return null;

  const parts: string[] = [];

  if (context.view) {
    parts.push(`Viewing: ${context.view}`);
  }

  if (context.elementName) {
    parts.push(`About: ${context.elementName}`);
  } else if (context.elementType && context.elementId) {
    parts.push(`About: ${context.elementType} (${context.elementId})`);
  }

  if (context.selection) {
    const truncated = context.selection.length > 50
      ? context.selection.slice(0, 50) + '...'
      : context.selection;
    parts.push(`Selected: "${truncated}"`);
  }

  return parts.length > 0 ? parts.join(' • ') : null;
}

// Hook for global keyboard shortcut
export function useFloatingInput() {
  const [isVisible, setIsVisible] = useState(false);
  const [context, setContext] = useState<FloatingInputContext>({});

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K to open
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsVisible(true);

        // Capture any selected text
        const selection = window.getSelection()?.toString();
        if (selection) {
          setContext(prev => ({ ...prev, selection }));
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const open = useCallback((newContext?: FloatingInputContext) => {
    if (newContext) {
      setContext(prev => ({ ...prev, ...newContext }));
    }
    setIsVisible(true);
  }, []);

  const close = useCallback(() => {
    setIsVisible(false);
  }, []);

  const updateContext = useCallback((newContext: Partial<FloatingInputContext>) => {
    setContext(prev => ({ ...prev, ...newContext }));
  }, []);

  return {
    isVisible,
    context,
    open,
    close,
    updateContext,
    setIsVisible,
    setContext,
  };
}
