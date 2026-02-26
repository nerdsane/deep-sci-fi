"""Art generation service for world visual identity.

Generates portraits for dwellers and illustrations for regions.
Uses XAI Grok Imagine (same pipeline as story covers) and stores in Cloudflare R2.

Cost: ~$0.02/image (grok-imagine-image)
"""

import asyncio
import functools
import logging
import uuid

import openai
import os

from media.generator import generate_image
from storage.r2 import upload_media

logger = logging.getLogger(__name__)

_openai_client: openai.AsyncOpenAI | None = None

OPENAI_MODEL = "gpt-4.1-mini"

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


def _get_openai_client() -> openai.AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        _openai_client = openai.AsyncOpenAI(api_key=api_key)
    return _openai_client


async def _build_portrait_prompt(dweller: dict, world: dict) -> str:
    """Use OpenAI to craft a portrait prompt from dweller/world context."""
    client = _get_openai_client()

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

    response = await client.chat.completions.create(
        model=OPENAI_MODEL,
        max_tokens=200,
        messages=[
            {"role": "system", "content": PORTRAIT_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    prompt = response.choices[0].message.content.strip()
    logger.info(f"Generated portrait prompt for '{dweller['name']}': {prompt[:80]}...")
    return prompt


async def generate_dweller_portrait(
    dweller_id: str,
    dweller: dict,
    world: dict,
    image_prompt: str | None = None,
) -> str | None:
    """Generate a portrait for a dweller and store in R2.

    Args:
        dweller_id: UUID string for the dweller
        dweller: Dict with name, role, age, generation, cultural_identity,
                 origin_region, personality
        world: Dict with name, premise
        image_prompt: Optional agent-supplied prompt. If provided, used directly
                      for XAI image generation; skips OpenAI prompt engineering.

    Returns:
        Public URL of the uploaded portrait, or None on failure
    """
    try:
        if image_prompt:
            prompt = image_prompt
            logger.info(f"Using agent-supplied image_prompt for dweller {dweller_id}")
        else:
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
