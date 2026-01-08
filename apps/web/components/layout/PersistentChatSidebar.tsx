'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useChatStore, type ChatMessage, type CurrentAgent } from '@/lib/chat-store';
import { useNavigationContext } from '@/lib/use-navigation-context';
import { trpc } from '@/lib/trpc';
import { Message } from '../chat/Message';
import { ChatInput } from '../chat/ChatInput';
import type { AgentStatus } from '../chat/ChatPanel';
import '../chat/chat-canvas.css';

/**
 * PersistentChatSidebar - Left sidebar chat that persists across all navigation
 *
 * Responsibilities:
 * - Displays all chat messages (persisted in Zustand store)
 * - Handles agent switching based on navigation context
 * - Sends messages to appropriate agent (User Agent or World Agent)
 * - Adds system messages when switching agents
 * - Supports hybrid navigation (chat commands + clicking)
 */
export function PersistentChatSidebar() {
  const router = useRouter();
  const { messages, currentAgent, addMessage, addSystemMessage, switchAgent } = useChatStore();
  const context = useNavigationContext();

  const [agentStatus, setAgentStatus] = useState<AgentStatus>('idle');
  const [inputValue, setInputValue] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Get User Agent (always fetch)
  const { data: userAgent } = trpc.agents.getUserAgent.useQuery();

  // Get World Agent if in world context (only when worldId present)
  const { data: worldAgent } = trpc.agents.getOrCreateWorldAgent.useQuery(
    { worldId: context.worldId! },
    { enabled: !!context.worldId }
  );

  // Get world details for display (only when worldId present)
  const { data: world } = trpc.worlds.getById.useQuery(
    { id: context.worldId! },
    { enabled: !!context.worldId }
  );

  // Send message mutation
  const sendMessageMutation = trpc.chat.sendMessage.useMutation({
    onMutate: () => {
      setAgentStatus('thinking');
    },
    onSuccess: (response) => {
      // Add agent response messages to chat
      const agentMessages = response.messages
        .filter(msg => msg.role === 'agent')
        .map((msg, idx) => ({
          id: `agent-${Date.now()}-${idx}`,
          role: msg.role as 'agent',
          content: msg.content,
          timestamp: new Date(),
          agentType: currentAgent?.type,
          worldId: currentAgent?.worldId,
          worldName: currentAgent?.worldName,
        }));

      agentMessages.forEach(msg => addMessage(msg));
      setAgentStatus('idle');
    },
    onError: (error) => {
      console.error('Failed to send message:', error);
      addSystemMessage(`Error: ${error.message}`);
      setAgentStatus('error');

      // Reset to idle after 2 seconds
      setTimeout(() => setAgentStatus('idle'), 2000);
    },
  });

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Switch agents when navigation context changes
  useEffect(() => {
    // If in world context and world agent is loaded
    if (context.worldId && worldAgent) {
      const targetAgent: CurrentAgent = {
        type: 'world',
        id: worldAgent.agentId,
        worldId: context.worldId,
        worldName: world?.name,
      };

      // Only switch if different from current agent
      if (currentAgent?.id !== targetAgent.id) {
        switchAgent(targetAgent);
      }
    }
    // If in worlds list and user agent is loaded
    else if (context.type === 'worlds-list' && userAgent) {
      const targetAgent: CurrentAgent = {
        type: 'user',
        id: userAgent.agentId,
      };

      // Only switch if different from current agent
      if (currentAgent?.id !== targetAgent.id) {
        switchAgent(targetAgent);
      }
    }
  }, [context, userAgent, worldAgent, world, currentAgent, switchAgent]);

  // Add welcome message if no messages
  useEffect(() => {
    if (messages.length === 0 && currentAgent) {
      const welcomeMessage = getWelcomeMessage(context.type, currentAgent.worldName);
      if (welcomeMessage) {
        addMessage({
          id: 'welcome',
          role: 'agent',
          content: welcomeMessage,
          timestamp: new Date(),
          agentType: currentAgent.type,
          worldId: currentAgent.worldId,
          worldName: currentAgent.worldName,
        });
      }
    }
  }, [currentAgent, messages.length, context.type, addMessage]);

  const handleSendMessage = async () => {
    const message = inputValue.trim();
    if (!message) return;

    // Clear input immediately
    setInputValue('');

    // Add user message to store immediately
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date(),
    };

    addMessage(userMessage);

    // Check for navigation commands
    const navCommand = parseNavigationCommand(message, context);
    if (navCommand) {
      // Navigate to the specified path
      router.push(navCommand.path);
      addSystemMessage(navCommand.message);
      return;
    }

    // Send to appropriate agent via tRPC
    sendMessageMutation.mutate({
      message,
      context: {
        worldId: context.worldId || undefined,
        storyId: context.storyId || undefined,
      },
    });
  };

  return (
    <aside className="persistent-chat-sidebar">
      <div className="chat-header">
        <div className="chat-header-logo">
          <pre className="logo-ascii">
{`██████╗ ███████╗███████╗██████╗
██╔══██╗██╔════╝██╔════╝██╔══██╗
██║  ██║█████╗  █████╗  ██████╔╝
██║  ██║██╔══╝  ██╔══╝  ██╔═══╝
██████╔╝███████╗███████╗██║
╚═════╝ ╚══════╝╚══════╝╚═╝
███████╗ ██████╗██╗      ███████╗██╗
██╔════╝██╔════╝██║      ██╔════╝██║
███████╗██║     ██║█████╗█████╗  ██║
╚════██║██║     ██║╚════╝██╔══╝  ██║
███████║╚██████╗██║      ██║     ██║
╚══════╝ ╚═════╝╚═╝      ╚═╝     ╚═╝`}
          </pre>
        </div>
        <div className="chat-header-agent">
          <span className="agent-indicator"></span>
          {currentAgent ? (
            <span>
              {currentAgent.type === 'user'
                ? 'User Agent'
                : `World Agent${currentAgent.worldName ? ` - ${currentAgent.worldName}` : ''}`
              }
            </span>
          ) : (
            <span>Connecting...</span>
          )}
        </div>
      </div>

      <div className="message-list">
        {messages.map((message) => (
          <Message
            key={message.id}
            role={message.role}
            content={message.content}
            timestamp={message.timestamp}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <ChatInput
          value={inputValue}
          onChange={setInputValue}
          onSend={handleSendMessage}
          disabled={agentStatus === 'thinking'}
          placeholder={getPlaceholder(context.type)}
        />
      </div>
    </aside>
  );
}

/**
 * Get context-appropriate welcome message
 */
function getWelcomeMessage(contextType: string, worldName?: string): string | null {
  if (contextType === 'story') {
    return "I'm ready to continue your story. What happens next?";
  }

  if (contextType === 'world') {
    return `I'm here to help you explore and expand ${worldName || 'this world'}. What would you like to know or add?`;
  }

  if (contextType === 'worlds-list') {
    return "Welcome! I can help you create new worlds, explore existing ones, or answer questions about your projects. What would you like to do?";
  }

  return null;
}

/**
 * Get context-appropriate input placeholder
 */
function getPlaceholder(contextType: string): string {
  if (contextType === 'story') {
    return "Continue the story, or ask about the world...";
  }

  if (contextType === 'world') {
    return "Ask me about this world or create a story...";
  }

  return "Ask me to create a world, or select a world to work on...";
}

/**
 * Parse navigation commands from user input
 */
function parseNavigationCommand(
  message: string,
  context: ReturnType<typeof useNavigationContext>
): { path: string; message: string } | null {
  const lower = message.toLowerCase().trim();

  // "show my worlds" or "go home"
  if (lower.includes('show my worlds') || lower.includes('go home') || lower === 'home') {
    return {
      path: '/worlds',
      message: 'Navigating to worlds list...',
    };
  }

  // "go back" from story to world
  if (lower.includes('go back') && context.type === 'story' && context.worldId) {
    return {
      path: `/worlds/${context.worldId}`,
      message: 'Returning to world...',
    };
  }

  // "go back" from world to worlds list
  if (lower.includes('go back') && context.type === 'world') {
    return {
      path: '/worlds',
      message: 'Returning to worlds list...',
    };
  }

  // TODO: Add more navigation commands:
  // - "open world X"
  // - "show story Y"
  // - etc.

  return null;
}
