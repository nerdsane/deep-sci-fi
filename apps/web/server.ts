/**
 * Custom Next.js Server with WebSocket Support
 *
 * This server wraps the Next.js application and adds WebSocket support
 * for real-time communication between agents and the Canvas UI.
 *
 * Usage:
 *   Development: bun run dev:server (or tsx watch server.ts)
 *   Production: bun run build && bun run start:server
 */

import { createServer } from 'http';
import { parse } from 'url';
import next from 'next';
import { initializeWebSocketServer, shutdownWebSocketServer, getWebSocketManager } from './lib/websocket';

const dev = process.env.NODE_ENV !== 'production';
const hostname = process.env.HOST || 'localhost';
const port = parseInt(process.env.PORT || '3000', 10);

// Initialize Next.js
const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();

async function main() {
  try {
    // Prepare Next.js
    await app.prepare();

    // Create HTTP server
    const server = createServer(async (req, res) => {
      try {
        const parsedUrl = parse(req.url || '', true);
        await handle(req, res, parsedUrl);
      } catch (err) {
        console.error('Error handling request:', err);
        res.statusCode = 500;
        res.end('Internal server error');
      }
    });

    // Initialize WebSocket server on /ws path
    initializeWebSocketServer(server, '/ws');

    // Start listening
    server.listen(port, () => {
      console.log(`
╔══════════════════════════════════════════════════════════════════╗
║                    Deep Sci-Fi Web Server                        ║
╠══════════════════════════════════════════════════════════════════╣
║  Mode:        ${dev ? 'Development' : 'Production'}                                       ║
║  HTTP:        http://${hostname}:${port}                                  ║
║  WebSocket:   ws://${hostname}:${port}/ws                               ║
╚══════════════════════════════════════════════════════════════════╝
      `);

      // Log initial WebSocket stats
      const manager = getWebSocketManager();
      const stats = manager.getStats();
      console.log('[WebSocket] Initial stats:', stats);
    });

    // Graceful shutdown
    const shutdown = async (signal: string) => {
      console.log(`\n[Server] Received ${signal}, shutting down gracefully...`);

      try {
        await shutdownWebSocketServer();
        server.close(() => {
          console.log('[Server] HTTP server closed');
          process.exit(0);
        });

        // Force exit after 10 seconds
        setTimeout(() => {
          console.error('[Server] Forced shutdown after timeout');
          process.exit(1);
        }, 10000);
      } catch (error) {
        console.error('[Server] Error during shutdown:', error);
        process.exit(1);
      }
    };

    process.on('SIGINT', () => shutdown('SIGINT'));
    process.on('SIGTERM', () => shutdown('SIGTERM'));

  } catch (error) {
    console.error('[Server] Failed to start:', error);
    process.exit(1);
  }
}

main();
