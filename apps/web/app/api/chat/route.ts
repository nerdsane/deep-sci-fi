import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const { message } = await request.json();

    // TODO: Connect to Letta agent API
    // For now, return a placeholder response
    console.log('[Chat API] Received message:', message);

    // In the future, this will:
    // 1. Get or create a Letta agent
    // 2. Send the message to the agent
    // 3. Return the agent's response

    return NextResponse.json({
      response: `I received your message: "${message}". The Letta agent integration is coming soon. For now, use the Canvas UI to explore worlds and stories.`,
    });
  } catch (error) {
    console.error('Chat API error:', error);
    return NextResponse.json(
      { error: 'Failed to process message' },
      { status: 500 }
    );
  }
}
