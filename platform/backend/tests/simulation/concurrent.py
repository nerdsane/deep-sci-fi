"""Deterministic concurrent request runner for DST.

Replaces ThreadPoolExecutor with single-threaded asyncio tasks.
BUGGIFY delays (asyncio.sleep with seeded durations) become deterministic
yield points that control interleaving order.

Why this is deterministic: asyncio's event loop is single-threaded. When two
tasks both call asyncio.sleep(duration), the one with the shorter duration
resumes first. The durations come from buggify_delay() which uses the seeded
RNG. When durations are equal, asyncio uses FIFO (creation order).
"""

import asyncio

from httpx import ASGITransport, AsyncClient


async def run_concurrent_requests(app, requests: list[dict]) -> list:
    """Run multiple ASGI requests as concurrent asyncio tasks.

    Args:
        app: The ASGI application (FastAPI app).
        requests: List of dicts with keys matching httpx.AsyncClient.request()
                  params (method, url, headers, json, etc.).

    Returns:
        List of httpx.Response objects in the same order as requests.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tasks = [asyncio.create_task(client.request(**req)) for req in requests]
        return list(await asyncio.gather(*tasks))
