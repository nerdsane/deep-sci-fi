import { db } from '@deep-sci-fi/db';
import { getLettaOrchestrator } from '@deep-sci-fi/letta';
import type { StreamChunk } from '@deep-sci-fi/letta';

// Development test user email
const DEV_USER_EMAIL = 'dev@deep-sci-fi.local';

/**
 * Get or create a development test user
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
  }

  return user;
}

/**
 * SSE streaming endpoint for agent chat
 * Returns Server-Sent Events with StreamChunk payloads
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { message, worldId, storyId } = body;

    if (!message || typeof message !== 'string') {
      return new Response(
        JSON.stringify({ error: 'Message is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      );
    }

    const user = await getOrCreateDevUser();
    const orchestrator = getLettaOrchestrator(db);

    // Create a readable stream that yields SSE events
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      async start(controller) {
        try {
          // Get the async generator from orchestrator
          const generator = orchestrator.sendMessageStreaming(
            user.id,
            message,
            { worldId: worldId || undefined, storyId: storyId || undefined }
          );

          // Yield each chunk as an SSE event
          for await (const chunk of generator) {
            const data = `data: ${JSON.stringify(chunk)}\n\n`;
            controller.enqueue(encoder.encode(data));
          }

          // Send done event
          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
          controller.close();
        } catch (error) {
          // Send error as SSE event
          const errorChunk: StreamChunk = {
            type: 'error',
            content: error instanceof Error ? error.message : String(error),
          };
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(errorChunk)}\n\n`));
          controller.close();
        }
      },
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no', // Disable nginx buffering
      },
    });
  } catch (error) {
    console.error('[Chat Stream API] Error:', error);

    const errorMessage = error instanceof Error ? error.message : String(error);
    const isConnectionError = errorMessage.includes('ECONNREFUSED') ||
                              errorMessage.includes('fetch failed');

    if (isConnectionError) {
      return new Response(
        JSON.stringify({
          error: 'Letta server is not running',
          details: errorMessage,
        }),
        { status: 503, headers: { 'Content-Type': 'application/json' } }
      );
    }

    return new Response(
      JSON.stringify({
        error: 'Failed to process message',
        details: errorMessage,
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    );
  }
}
