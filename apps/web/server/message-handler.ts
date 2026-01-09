/**
 * Message Handler
 *
 * Processes incoming WebSocket messages and routes them to the appropriate handlers.
 * Integrates with the Letta orchestrator for agent communication.
 */

import { db } from '@deep-sci-fi/db';
import { getLettaOrchestrator, setActiveBroadcastHandler } from '@deep-sci-fi/letta';
import type { StreamChunk } from '@deep-sci-fi/letta';
import type {
  Session,
  Client,
  ClientToServerMessage,
  ChatMessage,
  InteractionMessage,
  ChatChunkMessage,
  StateChangeMessage,
  ServerToClientMessage,
} from './types';
import {
  broadcastToSession,
  queueInteraction,
  updateSessionContext,
  getSessionContext,
} from './session-manager';

// Development test user ID
const DEV_USER_EMAIL = 'dev@deep-sci-fi.local';

/**
 * Get or create a development test user
 */
async function getOrCreateDevUser(): Promise<{ id: string; email: string }> {
  let user = await db.user.findUnique({
    where: { email: DEV_USER_EMAIL },
  });

  if (!user) {
    user = await db.user.create({
      data: {
        email: DEV_USER_EMAIL,
        name: 'Development User',
      },
    });
    console.log('[Message Handler] Created development user:', user.id);
  }

  return user;
}

/**
 * Handle incoming messages from clients
 */
export async function handleMessage(
  session: Session,
  client: Client,
  message: ClientToServerMessage
): Promise<void> {
  console.log(`[Message Handler] ${client.type}:${client.id} sent ${message.type}`);

  switch (message.type) {
    case 'chat_message':
      await handleChatMessage(session, client, message);
      break;

    case 'interaction':
      await handleInteraction(session, client, message);
      break;

    case 'ping':
      // Pong is handled at the server level
      break;

    default:
      console.warn(`[Message Handler] Unknown message type: ${(message as any).type}`);
  }
}

/**
 * Handle chat messages - send to agent and stream response
 */
async function handleChatMessage(
  session: Session,
  client: Client,
  message: ChatMessage
): Promise<void> {
  const { content, context } = message;

  console.log(`[Message Handler] Chat message from ${client.id}: ${content.substring(0, 50)}...`);

  // Update session context if provided
  if (context?.worldId || context?.storyId) {
    updateSessionContext(session.id, context);
  }

  // Get the effective context (from message or session)
  const effectiveContext = {
    ...getSessionContext(session.id),
    ...context,
  };

  // Create a broadcast handler that routes tool messages to this session
  const sessionBroadcastHandler = (message: any) => {
    broadcastToSession(session.id, message as ServerToClientMessage);
  };

  try {
    // Set the broadcast handler so tools can send messages to this session
    setActiveBroadcastHandler(sessionBroadcastHandler);

    // Notify all clients that agent is thinking
    broadcastToSession(session.id, {
      type: 'state_change',
      event: 'agent_thinking',
      data: { message: content.substring(0, 100) },
    } as StateChangeMessage);

    // Get orchestrator with database
    const orchestrator = getLettaOrchestrator(db);

    // Get user
    const user = await getOrCreateDevUser();

    // Stream response from agent
    const generator = orchestrator.sendMessageStreaming(user.id, content, {
      worldId: effectiveContext?.worldId,
      storyId: effectiveContext?.storyId,
    });

    // Process each chunk and broadcast to session
    for await (const chunk of generator) {
      const chatChunk: ChatChunkMessage = {
        type: 'chat_chunk',
        chunk,
      };

      broadcastToSession(session.id, chatChunk);
    }

    // Notify agent is done
    broadcastToSession(session.id, {
      type: 'state_change',
      event: 'agent_done',
      data: {},
    } as StateChangeMessage);

  } catch (error) {
    console.error('[Message Handler] Error processing chat message:', error);

    // Send error to all clients
    broadcastToSession(session.id, {
      type: 'chat_chunk',
      chunk: {
        type: 'error',
        content: error instanceof Error ? error.message : 'Failed to process message',
      },
    } as ChatChunkMessage);

    // Notify agent is done (even on error)
    broadcastToSession(session.id, {
      type: 'state_change',
      event: 'agent_done',
      data: { error: true },
    } as StateChangeMessage);
  } finally {
    // Always clear the broadcast handler when done
    setActiveBroadcastHandler(null);
  }
}

/**
 * Handle canvas interactions - queue for agent polling
 */
async function handleInteraction(
  session: Session,
  client: Client,
  message: InteractionMessage
): Promise<void> {
  const { componentId, interactionType, data, target } = message;

  console.log(
    `[Message Handler] Interaction from ${client.id}: ${interactionType} on ${componentId}`
  );

  // Queue the interaction for agent polling
  queueInteraction(session.id, componentId, interactionType, data, target);

  // Broadcast interaction to other clients (for visibility, especially CLI)
  broadcastToSession(
    session.id,
    {
      type: 'state_change',
      event: 'agent_thinking',
      data: {
        trigger: 'interaction',
        componentId,
        interactionType,
      },
    } as StateChangeMessage,
    client.id // Exclude sender
  );
}

/**
 * Broadcast a canvas UI update to a session
 * Called by tools when they want to update the canvas
 */
export function broadcastCanvasUI(
  sessionId: string,
  action: 'create' | 'update' | 'remove',
  target: string,
  componentId: string,
  spec?: any,
  mode: 'overlay' | 'fullscreen' | 'inline' = 'overlay'
): void {
  broadcastToSession(sessionId, {
    type: 'canvas_ui',
    action,
    target,
    componentId,
    spec,
    mode,
  });
}

/**
 * Broadcast a state change to a session
 */
export function broadcastStateChange(
  sessionId: string,
  event: StateChangeMessage['event'],
  data: Record<string, any>
): void {
  broadcastToSession(sessionId, {
    type: 'state_change',
    event,
    data,
  });
}

/**
 * Broadcast a suggestion to a session
 */
export function broadcastSuggestion(
  sessionId: string,
  title: string,
  description: string,
  priority: 'high' | 'medium' | 'low',
  actionId: string,
  actionLabel?: string,
  actionData?: any
): void {
  broadcastToSession(sessionId, {
    type: 'suggestion',
    payload: {
      id: `sug-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      priority,
      title,
      description,
      actionId,
      actionLabel,
      actionData,
    },
  });
}
