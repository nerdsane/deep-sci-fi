import { NextResponse } from 'next/server';
import { db } from '@deep-sci-fi/db';
import { getLettaOrchestrator } from '@deep-sci-fi/letta';

// Development test user ID - in production, this would come from auth
const DEV_USER_EMAIL = 'dev@deep-sci-fi.local';

/**
 * Get or create a development test user
 * In production, this would be replaced with proper authentication
 */
async function getOrCreateDevUser() {
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
    console.log('[Chat API] Created development user:', user.id);
  }

  return user;
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { message, worldId, storyId } = body;

    if (!message || typeof message !== 'string') {
      return NextResponse.json(
        { error: 'Message is required' },
        { status: 400 }
      );
    }

    console.log('[Chat API] Received message:', message.substring(0, 100));
    console.log('[Chat API] Context:', { worldId, storyId });

    // Get or create development user
    // TODO: Replace with proper auth in production
    const user = await getOrCreateDevUser();

    // Get orchestrator with database client
    const orchestrator = getLettaOrchestrator(db);

    // Send message to appropriate agent based on context
    const response = await orchestrator.sendMessage(
      user.id,
      message,
      {
        worldId: worldId || undefined,
        storyId: storyId || undefined,
      }
    );

    console.log('[Chat API] Agent response:', {
      messageCount: response.messages.length,
      toolCallCount: response.toolCalls?.length ?? 0,
    });

    // Return the response
    return NextResponse.json({
      messages: response.messages,
      toolCalls: response.toolCalls ?? [],
      metadata: response.metadata,
    });
  } catch (error) {
    console.error('[Chat API] Error:', error);

    // Check if it's a Letta connection error
    const errorMessage = error instanceof Error ? error.message : String(error);
    const isConnectionError = errorMessage.includes('ECONNREFUSED') ||
                              errorMessage.includes('fetch failed') ||
                              errorMessage.includes('network');

    if (isConnectionError) {
      return NextResponse.json(
        {
          error: 'Letta server is not running. Start it with: cd letta && docker compose -f dev-compose.yaml up -d',
          details: errorMessage,
        },
        { status: 503 }
      );
    }

    return NextResponse.json(
      {
        error: 'Failed to process message',
        details: errorMessage,
      },
      { status: 500 }
    );
  }
}
