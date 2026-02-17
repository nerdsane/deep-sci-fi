"""Art generation service for world visual identity.

Generates portraits for dwellers and illustrations for regions.
Uses XAI Grok Imagine (same pipeline as story covers) and stores in Cloudflare R2.

Cost: ~$0.02/image (grok-imagine-image)
"""

import asyncio
import functools
import logging
import uuid

import anthropic
import os

from media.generator import generate_image
from storage.r2 import upload_media

logger = logging.getLogger(__name__)

_anthropic_client: anthropic.AsyncAnthropic | None = None

ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"

PORTRAIT_SYSTEM_PROMPT = """\
You are a visual prompt engineer for AI portrait generation (xAI Grok Imagine).
Given a sci-fi character's description, craft a prompt for a character portrait.

Rules:
- Output ONLY the prompt text, no preamble or explanation
- Portrait style: square format, cinematic sci-fi character portrait
- Include: face/upper body composition, lighting mood, clothing hints, atmospheric detail
- Reflect the character's role and cultural background in visual details
- Never include text, words, letters, or UI elements
- Style: painterly sci-fi portrait, dramatic lighting, detailed
- Keep under 150 words
"""


def _get_anthropic_client() -> anthropic.AsyncAnthropic:
    global _anthropic_client
    if _anthropic_client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        _anthropic_client = anthropic.AsyncAnthropic(api_key=api_key)
    return _anthropic_client


async def _build_portrait_prompt(dweller: dict, world: dict) -> str:
    """Use Claude Haiku to craft a portrait prompt from dweller/world context."""
    client = _get_anthropic_client()

    context_parts = [
        f"Character name: {dweller['name']}",
        f"Role: {dweller.get('role', 'unknown')}",
    ]
    if dweller.get("generation"):
        context_parts.append(f"Generation: {dweller['generation']}")
    if dweller.get("origin_region"):
        context_parts.append(f"Origin region: {dweller['origin_region']}")
    context_parts.extend([
        f"World: {world['name']}",
        f"World premise: {world['premise'][:300]}",
    ])
    if dweller.get("personality"):
        context_parts.append(f"Personality: {dweller['personality'][:200]}")

    user_message = "\n".join(context_parts)

    response = await client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=200,
        system=PORTRAIT_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    prompt = response.content[0].text.strip()
    logger.info(f"Generated portrait prompt for '{dweller['name']}': {prompt[:80]}...")
    return prompt


async def generate_dweller_portrait(
    dweller_id: str,
    dweller: dict,
    world: dict,
) -> str | None:
    """Generate a portrait for a dweller and store in R2.

    Args:
        dweller_id: UUID string for the dweller
        dweller: Dict with name, role, age, generation, cultural_identity,
                 origin_region, personality
        world: Dict with name, premise

    Returns:
        Public URL of the uploaded portrait, or None on failure
    """
    try:
        prompt = await _build_portrait_prompt(dweller, world)
        image_bytes = await generate_image(prompt)

        storage_key = f"media/dwellers/{dweller_id}/portrait/{uuid.uuid4()}.png"
        # upload_media is synchronous (boto3); run in executor to avoid blocking the event loop
        loop = asyncio.get_running_loop()
        portrait_url = await loop.run_in_executor(
            None, functools.partial(upload_media, image_bytes, storage_key, "image/png")
        )

        logger.info(f"Portrait generated for dweller {dweller_id}: {portrait_url}")
        return portrait_url

    except Exception:
        logger.exception(f"Portrait generation failed for dweller {dweller_id}")
        return None
