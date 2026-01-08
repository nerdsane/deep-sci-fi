/**
 * FeedbackContext - Global feedback state management
 *
 * Provides toast notifications and agent status throughout the app
 */
import React, { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

export interface ToastData {
  id: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'agent';
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export interface AgentStatusData {
  isThinking: boolean;
  action?: string;
  progress?: number;
}

interface FeedbackContextValue {
  // Toast management
  toasts: ToastData[];
  showToast: (message: string, type?: ToastData['type'], options?: {
    duration?: number;
    action?: ToastData['action'];
  }) => string;
  dismissToast: (id: string) => void;
  clearAllToasts: () => void;

  // Agent status
  agentStatus: AgentStatusData;
  setAgentThinking: (thinking: boolean, action?: string) => void;
  setAgentProgress: (progress: number) => void;
}

const FeedbackContext = createContext<FeedbackContextValue | null>(null);

export function useFeedback() {
  const context = useContext(FeedbackContext);
  if (!context) {
    throw new Error('useFeedback must be used within a FeedbackProvider');
  }
  return context;
}

// Safe version that doesn't throw
export function useFeedbackSafe() {
  return useContext(FeedbackContext);
}

let toastIdCounter = 0;

export function FeedbackProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastData[]>([]);
  const [agentStatus, setAgentStatus] = useState<AgentStatusData>({
    isThinking: false,
  });

  const showToast = useCallback((
    message: string,
    type: ToastData['type'] = 'info',
    options?: { duration?: number; action?: ToastData['action'] }
  ) => {
    const id = `toast-${Date.now()}-${++toastIdCounter}`;
    const toast: ToastData = {
      id,
      message,
      type,
      duration: options?.duration ?? 5000,
      action: options?.action,
    };

    setToasts(prev => {
      // Limit to 5 toasts max
      const newToasts = [...prev, toast];
      if (newToasts.length > 5) {
        return newToasts.slice(-5);
      }
      return newToasts;
    });

    return id;
  }, []);

  const dismissToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const clearAllToasts = useCallback(() => {
    setToasts([]);
  }, []);

  const setAgentThinking = useCallback((thinking: boolean, action?: string) => {
    setAgentStatus(prev => ({
      ...prev,
      isThinking: thinking,
      action: thinking ? action : undefined,
      progress: thinking ? prev.progress : undefined,
    }));
  }, []);

  const setAgentProgress = useCallback((progress: number) => {
    setAgentStatus(prev => ({
      ...prev,
      progress,
    }));
  }, []);

  const value: FeedbackContextValue = {
    toasts,
    showToast,
    dismissToast,
    clearAllToasts,
    agentStatus,
    setAgentThinking,
    setAgentProgress,
  };

  return (
    <FeedbackContext.Provider value={value}>
      {children}
    </FeedbackContext.Provider>
  );
}
