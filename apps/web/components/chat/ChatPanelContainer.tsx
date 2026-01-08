'use client';

import { useState, useEffect } from 'react';
import { ChatPanel, type ChatContext, type MessageType, type AgentStatus, type ViewMode } from './ChatPanel';
import { trpc } from '@/lib/trpc';

interface ChatPanelContainerProps {
  worldId?: string;
  storyId?: string;
  viewMode?: ViewMode;
  isMobile?: boolean;
  placeholder?: string;
}

/**
 * ChatPanelContainer - Connects ChatPanel to Letta Agent System
 *
 * Responsibilities:
 * - Manages chat message state
 * - Gets appropriate agent (User Agent or World Agent)
 * - Sends messages via tRPC to Letta orchestrator
 * - Handles agent status (thinking/idle/error)
 */
export function ChatPanelContainer({
  worldId,
  storyId,
  viewMode = 'canvas',
  isMobile = false,
  placeholder,
}: ChatPanelContainerProps) {
  const [messages, setMessages] = useState<MessageType[]>([]);
  const [agentStatus, setAgentStatus] = useState<AgentStatus>('idle');

  // Get User Agent (orchestrator) - always available
  const { data: userAgent } = trpc.agents.getUserAgent.useQuery(undefined, {
    enabled: !worldId, // Only fetch if no world context
  });

  // Get World Agent if in world context
  const { mutate: getWorldAgent } = trpc.agents.getOrCreateWorldAgent.useMutation();

  // Set story context mutation
  const { mutate: setStoryContext } = trpc.agents.setStoryContext.useMutation();

  // Send message mutation
  const sendMessageMutation = trpc.chat.sendMessage.useMutation({
    onMutate: () => {
      setAgentStatus('thinking');
    },
    onSuccess: (response) => {
      // Add agent response messages to chat
      // Note: response.messages is an array of AgentMessage objects
      const agentMessages = response.messages
        .filter(msg => msg.role === 'agent')
        .map((msg, idx) => ({
          id: `agent-${Date.now()}-${idx}`,
          role: msg.role as 'agent',
          content: msg.content,
          timestamp: new Date(),
          type: 'text' as const,
        }));

      setMessages((prev) => [...prev, ...agentMessages]);
      setAgentStatus('idle');
    },
    onError: (error) => {
      console.error('Failed to send message:', error);
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          role: 'system',
          content: `Error: ${error.message}`,
          timestamp: new Date(),
          type: 'text',
        },
      ]);
      setAgentStatus('error');

      // Reset to idle after 2 seconds
      setTimeout(() => setAgentStatus('idle'), 2000);
    },
  });

  // Set story context when viewing a story
  useEffect(() => {
    if (storyId && worldId) {
      // Get world agent first
      getWorldAgent({ worldId }, {
        onSuccess: (worldAgent) => {
          // Then set story context in the world agent's memory
          setStoryContext({
            agentId: worldAgent.agentId,
            storyId: storyId,
          }, {
            onSuccess: () => {
              console.log(`Story context set for agent ${worldAgent.agentId}: ${storyId}`);
            },
            onError: (error) => {
              console.error('Failed to set story context:', error);
            },
          });
        },
      });
    }
  }, [storyId, worldId, getWorldAgent, setStoryContext]);

  const handleSendMessage = async (message: string, context: ChatContext) => {
    // Add user message to UI immediately
    const userMessage: MessageType = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      timestamp: new Date(),
      type: 'text',
    };

    setMessages((prev) => [...prev, userMessage]);

    // Send to agent
    sendMessageMutation.mutate({
      message,
      context: {
        worldId: context.worldId,
        storyId: context.storyId,
      },
    });
  };

  // Add welcome message if no messages
  useEffect(() => {
    if (messages.length === 0) {
      const welcomeMessage = getWelcomeMessage(worldId, storyId);
      if (welcomeMessage) {
        setMessages([{
          id: 'welcome',
          role: 'agent',
          content: welcomeMessage,
          timestamp: new Date(),
          type: 'text',
        }]);
      }
    }
  }, [worldId, storyId, messages.length]);

  return (
    <ChatPanel
      worldId={worldId}
      storyId={storyId}
      messages={messages}
      onSendMessage={handleSendMessage}
      agentStatus={agentStatus}
      viewMode={viewMode}
      isMobile={isMobile}
    />
  );
}

/**
 * Get context-appropriate welcome message
 */
function getWelcomeMessage(worldId?: string, storyId?: string): string | null {
  if (storyId) {
    return "I'm ready to continue your story. What happens next?";
  }

  if (worldId) {
    return "I'm here to help you explore and expand this world. What would you like to know or add?";
  }

  // User Agent (orchestrator) context
  return "Welcome! I can help you create new worlds, explore existing ones, or answer questions about your projects. What would you like to do?";
}
