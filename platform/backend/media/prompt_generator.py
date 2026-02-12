"""LLM-powered prompt generation for media backfill.

Uses Claude Haiku to craft high-quality, content-specific image and video prompts
from story content and world context.
"""

import logging
import os

import anthropic

logger = logging.getLogger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def _get_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set — required for LLM prompt generation")
        _client = anthropic.AsyncAnthropic(api_key=api_key)
    return _client


MODEL = "claude-haiku-4-5-20251001"

IMAGE_SYSTEM_PROMPT = """\
You are a visual prompt engineer for AI image generation (xAI Grok Imagine).
Given a sci-fi story or world description, craft a specific, detailed image generation prompt.

Rules:
- Output ONLY the prompt text, no preamble or explanation
- Be specific about: composition, lighting, color palette, atmosphere, camera angle
- Focus on a single striking visual moment or landscape
- Never include text, words, letters, or UI elements in the scene
- Style: cinematic, photorealistic sci-fi concept art
- Keep under 200 words
"""

VIDEO_SYSTEM_PROMPT = """\
You are a visual prompt engineer for AI video generation (xAI Grok Imagine).
Given a sci-fi story, craft a prompt for a 10-second cinematic scene.

Rules:
- Output ONLY the prompt text, no preamble or explanation
- Describe a single continuous camera movement or scene moment
- Include: subject motion, camera movement, lighting shifts, atmosphere
- Focus on the most visually dramatic moment from the story
- Never include text, words, letters, or UI elements
- Style: cinematic sci-fi, smooth camera motion
- Keep under 150 words
"""

WORLD_COVER_SYSTEM_PROMPT = """\
You are a visual prompt engineer for AI image generation (xAI Grok Imagine).
Given a sci-fi world's premise and scientific basis, craft a prompt for a landscape cover image.

Rules:
- Output ONLY the prompt text, no preamble or explanation
- Create an establishing shot / wide landscape that captures the world's essence
- Be specific about: terrain, sky, structures, atmosphere, scale
- Include environmental details that reflect the world's premise
- Never include text, words, letters, or UI elements
- Style: cinematic wide-angle sci-fi landscape, dramatic lighting
- Keep under 200 words
"""


async def generate_image_prompt(
    title: str,
    content: str,
    world_name: str,
    world_premise: str,
    year_setting: str | None = None,
    perspective: str | None = None,
    dweller_name: str | None = None,
) -> str:
    """Use Claude to craft a high-quality image generation prompt from story content."""
    client = _get_client()

    context_parts = [
        f"Story title: {title}",
        f"World: {world_name}",
        f"World premise: {world_premise[:500]}",
    ]
    if year_setting:
        context_parts.append(f"Year setting: {year_setting}")
    if perspective:
        context_parts.append(f"Narrative perspective: {perspective}")
    if dweller_name:
        context_parts.append(f"Perspective character: {dweller_name}")

    # Use first ~2000 chars of content for context
    content_excerpt = content[:2000]
    context_parts.append(f"\nStory excerpt:\n{content_excerpt}")

    user_message = "\n".join(context_parts)

    response = await client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=IMAGE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    prompt = response.content[0].text.strip()
    logger.info(f"Generated image prompt for '{title}': {prompt[:80]}...")
    return prompt


async def generate_video_prompt(
    title: str,
    content: str,
    world_name: str,
    world_premise: str,
    year_setting: str | None = None,
    perspective: str | None = None,
    dweller_name: str | None = None,
) -> str:
    """Use Claude to craft a video scene prompt from story content."""
    client = _get_client()

    context_parts = [
        f"Story title: {title}",
        f"World: {world_name}",
        f"World premise: {world_premise[:500]}",
    ]
    if year_setting:
        context_parts.append(f"Year setting: {year_setting}")
    if perspective:
        context_parts.append(f"Narrative perspective: {perspective}")
    if dweller_name:
        context_parts.append(f"Perspective character: {dweller_name}")

    content_excerpt = content[:2000]
    context_parts.append(f"\nStory excerpt:\n{content_excerpt}")

    user_message = "\n".join(context_parts)

    response = await client.messages.create(
        model=MODEL,
        max_tokens=250,
        system=VIDEO_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    prompt = response.content[0].text.strip()
    logger.info(f"Generated video prompt for '{title}': {prompt[:80]}...")
    return prompt


async def generate_world_cover_prompt(
    name: str,
    premise: str,
    year_setting: int | None = None,
    scientific_basis: str | None = None,
) -> str:
    """Use Claude to craft a world cover image prompt from premise and science."""
    client = _get_client()

    context_parts = [
        f"World name: {name}",
        f"Premise: {premise}",
    ]
    if year_setting:
        context_parts.append(f"Year setting: {year_setting}")
    if scientific_basis:
        context_parts.append(f"Scientific basis: {scientific_basis[:500]}")

    user_message = "\n".join(context_parts)

    response = await client.messages.create(
        model=MODEL,
        max_tokens=300,
        system=WORLD_COVER_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    prompt = response.content[0].text.strip()
    logger.info(f"Generated world cover prompt for '{name}': {prompt[:80]}...")
    return prompt
