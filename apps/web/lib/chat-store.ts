import { create } from 'zustand';

/**
 * Chat message in the persistent chat sidebar
 */
export interface ChatMessage {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  timestamp: Date;
  agentType?: 'user' | 'world';
  worldId?: string;
  worldName?: string;
}

/**
 * Current active agent
 */
export interface CurrentAgent {
  type: 'user' | 'world';
  id: string;
  worldId?: string;
  worldName?: string;
}

/**
 * Chat state interface
 */
interface ChatState {
  messages: ChatMessage[];
  currentAgent: CurrentAgent | null;
  addMessage: (message: ChatMessage) => void;
  addSystemMessage: (content: string) => void;
  switchAgent: (newAgent: CurrentAgent) => void;
  clearHistory: () => void;
}

/**
 * Persistent Chat Store - Zustand
 *
 * This store maintains:
 * - All chat messages across navigation
 * - Current active agent (User Agent or World Agent)
 * - System messages for agent switching
 *
 * The chat persists across all page navigation.
 */
export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  currentAgent: null,

  /**
   * Add a message to the chat
   */
  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  /**
   * Add a system message (for agent switching, navigation, etc.)
   */
  addSystemMessage: (content) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: `system-${Date.now()}`,
          role: 'system',
          content,
          timestamp: new Date(),
        },
      ],
    })),

  /**
   * Switch to a different agent (User Agent <-> World Agent)
   * Adds a system message to show the transition
   */
  switchAgent: (newAgent) =>
    set((state) => {
      // Don't switch if already on this agent
      if (state.currentAgent?.id === newAgent.id) {
        return state;
      }

      // Generate system message
      let systemMessage: string;
      if (newAgent.type === 'user') {
        systemMessage = 'Switching to User Agent';
      } else {
        systemMessage = `Switching to World Agent${newAgent.worldName ? ` for ${newAgent.worldName}` : ''}`;
      }

      return {
        currentAgent: newAgent,
        messages: [
          ...state.messages,
          {
            id: `system-${Date.now()}`,
            role: 'system',
            content: systemMessage,
            timestamp: new Date(),
          },
        ],
      };
    }),

  /**
   * Clear all chat history
   */
  clearHistory: () =>
    set(() => ({
      messages: [],
    })),
}));
