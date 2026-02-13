"""xAI Grok Imagine media generation service.

Calls the xAI API for image and video generation.
- Images: grok-imagine-image ($0.02/image)
- Videos: grok-imagine-video ($0.05/sec)
"""

import asyncio
import base64
import logging
import os

import httpx

logger = logging.getLogger(__name__)

XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_BASE_URL = "https://api.x.ai/v1"

# Retry config
MAX_RETRIES = 2
RETRY_BACKOFF_BASE = 2  # seconds


async def generate_image(prompt: str) -> bytes:
    """Generate an image using xAI Grok Imagine.

    Args:
        prompt: Text description of the image to generate

    Returns:
        Raw image bytes (PNG)

    Raises:
        RuntimeError: If generation fails after retries
    """
    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{XAI_BASE_URL}/images/generations",
                    headers={
                        "Authorization": f"Bearer {XAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "grok-imagine-image",
                        "prompt": prompt,
                        "n": 1,
                        "response_format": "b64_json",
                    },
                )
                response.raise_for_status()
                data = response.json()
                image_b64 = data["data"][0]["b64_json"]
                return base64.b64decode(image_b64)

        except (httpx.HTTPStatusError, httpx.TimeoutException, KeyError) as e:
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                logger.warning(f"Image generation attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)
            else:
                raise RuntimeError(f"Image generation failed after {MAX_RETRIES + 1} attempts: {e}") from e


async def generate_video(prompt: str, duration: int = 10) -> bytes:
    """Generate a video using xAI Grok Imagine.

    Args:
        prompt: Text description of the video to generate
        duration: Video duration in seconds (max 15)

    Returns:
        Raw video bytes (MP4)

    Raises:
        RuntimeError: If generation fails after retries
    """
    duration = min(duration, 15)  # Cap at 15 seconds

    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Start generation
                response = await client.post(
                    f"{XAI_BASE_URL}/videos/generations",
                    headers={
                        "Authorization": f"Bearer {XAI_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "grok-imagine-video",
                        "prompt": prompt,
                        "duration": duration,
                        "aspect_ratio": "16:9",
                        "resolution": "720p",
                    },
                )
                response.raise_for_status()
                data = response.json()

                # Poll for completion
                request_id = data["request_id"]
                while True:
                    await asyncio.sleep(5)
                    status_response = await client.get(
                        f"{XAI_BASE_URL}/videos/{request_id}",
                        headers={"Authorization": f"Bearer {XAI_API_KEY}"},
                    )
                    status_response.raise_for_status()
                    status_data = status_response.json()

                    # xAI returns 202 while processing, 200 with video.url when done
                    if status_response.status_code == 200 and "video" in status_data:
                        video_url = status_data["video"]["url"]
                        video_response = await client.get(video_url)
                        video_response.raise_for_status()
                        return video_response.content

                    if status_data.get("status") == "expired":
                        raise RuntimeError("Video generation expired before completion")

        except (httpx.HTTPStatusError, httpx.TimeoutException, KeyError) as e:
            if attempt < MAX_RETRIES:
                wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                logger.warning(f"Video generation attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                await asyncio.sleep(wait)
            else:
                raise RuntimeError(f"Video generation failed after {MAX_RETRIES + 1} attempts: {e}") from e
