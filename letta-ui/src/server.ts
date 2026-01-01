import index from './index.html';

const LETTA_API_BASE = process.env.LETTA_BASE_URL || 'http://localhost:8283';
const PORT = process.env.PORT || 3000;

Bun.serve({
  port: PORT,

  static: {
    '/': index,
  },

  async fetch(req) {
    const url = new URL(req.url);

    // API proxy to Letta server
    if (url.pathname.startsWith('/api/')) {
      return proxyToLetta(req);
    }

    // Serve the HTML for all other requests (SPA routing)
    return index;
  },

  development: {
    hmr: true,
  },
});

async function proxyToLetta(req: Request) {
  const url = new URL(req.url);
  const lettaPath = url.pathname.replace('/api', '');
  const lettaUrl = `${LETTA_API_BASE}${lettaPath}${url.search}`;

  try {
    const response = await fetch(lettaUrl, {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
      },
      body: req.method !== 'GET' && req.method !== 'HEAD' ? await req.text() : undefined,
    });

    return new Response(response.body, {
      status: response.status,
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'application/json',
        'Access-Control-Allow-Origin': '*',
      },
    });
  } catch (error) {
    return new Response(
      JSON.stringify({ error: 'Failed to proxy request to Letta API' }),
      { status: 502, headers: { 'Content-Type': 'application/json' } }
    );
  }
}

console.log(`🚀 Letta UI running at http://localhost:${PORT}`);
console.log(`📡 Proxying API requests to ${LETTA_API_BASE}`);
