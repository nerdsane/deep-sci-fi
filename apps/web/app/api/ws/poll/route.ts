/**
 * WebSocket Polling Endpoint
 *
 * Provides polling-based message delivery for Canvas UI updates.
 * Browser clients should poll this endpoint every 500ms to receive:
 * - canvas_ui messages (component create/update/remove)
 * - state_change messages (story_started, agent_thinking, etc.)
 * - suggestion messages (proactive agent suggestions)
 *
 * Usage:
 * GET /api/ws/poll?clientId=<unique-client-id>
 *
 * Response:
 * { messages: [...], clientCount: number, hasMore: boolean }
 */

import { NextRequest, NextResponse } from 'next/server';
import {
  getPendingMessages,
  hasPendingMessages,
  getClientCount,
} from '@deep-sci-fi/letta';

export async function GET(request: NextRequest) {
  try {
    // Get client ID from query params (for tracking connected clients)
    const { searchParams } = new URL(request.url);
    const clientId = searchParams.get('clientId');

    if (!clientId) {
      return NextResponse.json(
        { error: 'clientId query parameter is required' },
        { status: 400 }
      );
    }

    // Get pending messages (also updates client's last poll time)
    const messages = getPendingMessages(clientId);

    return NextResponse.json({
      messages,
      clientCount: getClientCount(),
      hasMore: hasPendingMessages(),
    });
  } catch (error) {
    console.error('[ws/poll] Error:', error);
    return NextResponse.json(
      { error: 'Failed to get messages' },
      { status: 500 }
    );
  }
}

/**
 * POST endpoint for sending interactions from browser to server.
 *
 * Usage:
 * POST /api/ws/poll
 * Body: { clientId: string, interaction: InteractionMessage }
 */
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { clientId, interaction } = body;

    if (!clientId) {
      return NextResponse.json(
        { error: 'clientId is required' },
        { status: 400 }
      );
    }

    if (!interaction) {
      return NextResponse.json(
        { error: 'interaction is required' },
        { status: 400 }
      );
    }

    // Import queueInteraction dynamically to avoid circular dependencies
    const { queueInteraction } = await import('@deep-sci-fi/letta');

    // Queue the interaction for agent polling
    queueInteraction({
      type: 'interaction',
      componentId: interaction.componentId,
      interactionType: interaction.interactionType,
      data: interaction.data,
      target: interaction.target,
    });

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('[ws/poll] Error queuing interaction:', error);
    return NextResponse.json(
      { error: 'Failed to queue interaction' },
      { status: 500 }
    );
  }
}
