"""Grok Imagine API integration for video generation.

Uses xAI's Grok Imagine API (OpenAI-compatible) for text-to-video generation.
API docs: https://x.ai/news/grok-imagine-api
"""

import os
import logging
from typing import Any
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

# Initialize client lazily
_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """Get or create the Grok Imagine API client."""
    global _client
    if _client is None:
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise ValueError("XAI_API_KEY environment variable not set")
        _client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.x.ai/v1",
        )
    return _client


async def generate_video(
    prompt: str,
    aspect_ratio: str = "16:9",
    duration: int = 5,
) -> dict[str, Any]:
    """Generate a video from a text prompt.

    Args:
        prompt: Description of the video to generate
        aspect_ratio: Video aspect ratio (16:9, 9:16, 1:1)
        duration: Video duration in seconds (max 8.7s)

    Returns:
        Dict with job_id, status, and url (when complete)
    """
    try:
        client = get_client()

        # Grok Imagine uses images.generate endpoint
        # Note: Size parameter is not supported by Grok API
        response = await client.images.generate(
            model="grok-2-image",
            prompt=prompt,
            n=1,
        )

        # For now, return image generation result
        # Video generation may use different endpoint when fully available
        if response.data:
            return {
                "status": "completed",
                "url": response.data[0].url,
                "revised_prompt": response.data[0].revised_prompt,
            }
        return {"status": "failed", "error": "No data in response"}

    except Exception as e:
        logger.error(f"Video generation failed: {e}")
        return {"status": "failed", "error": str(e)}


async def generate_story_video(
    world_name: str,
    world_premise: str,
    conversation_summary: str,
    characters: list[dict[str, str]],
    tone: str = "dramatic",
) -> dict[str, Any]:
    """Generate a short story video from world activity.

    Args:
        world_name: Name of the world
        world_premise: Core premise of the world
        conversation_summary: Summary of dweller conversation
        characters: List of character dicts with name and role
        tone: Video tone (dramatic, documentary, poetic, news)

    Returns:
        Dict with job_id, status, and url (when complete)
    """
    # Build cinematic prompt from story elements
    char_desc = ", ".join(
        f"{c['name']} ({c['role']})" for c in characters[:3]
    )

    tone_styles = {
        "dramatic": "cinematic, high contrast lighting, emotional close-ups",
        "documentary": "observational camera, natural lighting, intimate",
        "poetic": "ethereal, soft focus, metaphorical imagery",
        "news": "urgent, handheld camera, investigative",
    }
    style = tone_styles.get(tone, tone_styles["dramatic"])

    prompt = f"""Science fiction scene in {world_name}.
Setting: {world_premise[:200]}
Characters: {char_desc}
Scene: {conversation_summary[:300]}
Style: {style}
Mood: contemplative future, grounded sci-fi aesthetic"""

    result = await generate_video(prompt)

    # Add job tracking info
    if result.get("status") == "completed":
        import uuid
        result["job_id"] = str(uuid.uuid4())

    return result


async def generate_thumbnail(
    world_name: str,
    world_premise: str,
    style: str = "cinematic",
) -> dict[str, Any]:
    """Generate a thumbnail image for a world or story.

    Args:
        world_name: Name of the world
        world_premise: Core premise of the world
        style: Visual style for the thumbnail

    Returns:
        Dict with status and url
    """
    prompt = f"""Cinematic thumbnail for sci-fi world "{world_name}".
Setting: {world_premise[:300]}
Style: {style}, widescreen composition, dramatic lighting, no text"""

    return await generate_video(prompt)


def _derive_style_from_world(world_premise: str, year_setting: int) -> str:
    """Derive visual style keywords from world premise.

    Analyzes the premise to determine appropriate aesthetic.
    """
    premise_lower = world_premise.lower()

    # Check for common sci-fi aesthetics
    if any(w in premise_lower for w in ["cyber", "neon", "hacker", "digital", "virtual"]):
        return "cyberpunk aesthetic, neon accents, high contrast, tech wear"
    elif any(w in premise_lower for w in ["solar", "green", "ecology", "sustainable", "garden"]):
        return "solarpunk aesthetic, warm earth tones, organic shapes, hopeful"
    elif any(w in premise_lower for w in ["noir", "detective", "shadow", "rain", "dark"]):
        return "neo-noir aesthetic, dramatic shadows, muted colors, moody"
    elif any(w in premise_lower for w in ["desert", "sand", "wasteland", "post-apoc"]):
        return "post-apocalyptic aesthetic, dusty earth tones, rugged textures"
    elif any(w in premise_lower for w in ["space", "station", "orbit", "stellar"]):
        return "space opera aesthetic, sleek metallic surfaces, cosmic backdrop"
    elif any(w in premise_lower for w in ["bio", "genetic", "organic", "mutation"]):
        return "biopunk aesthetic, organic textures, unsettling beauty"
    elif year_setting > 2200:
        return "far future aesthetic, advanced materials, holographic accents"
    elif year_setting < 2050:
        return "near future aesthetic, recognizable technology, subtle enhancements"
    else:
        return "mid-century sci-fi aesthetic, retro-futuristic, clean lines"


async def generate_avatar(
    name: str,
    role: str,
    background: str,
    world_name: str,
    world_premise: str,
    year_setting: int,
) -> dict[str, Any]:
    """Generate a character avatar via xAI Grok.

    Creates a portrait that matches the world's aesthetic while
    representing the character's personality and role.

    Args:
        name: Character's name
        role: Character's role/occupation
        background: Character's background story
        world_name: Name of the world they inhabit
        world_premise: Core premise of the world (used for style)
        year_setting: Year the world is set in

    Returns:
        Dict with status, url, and prompt used
    """
    try:
        client = get_client()

        # Derive world style
        world_style = _derive_style_from_world(world_premise, year_setting)

        # Build character-focused prompt
        # Extract key personality traits from background
        background_snippet = background[:150] if background else ""

        prompt = f"""Portrait of {name}, a {role} in the year {year_setting}.

Character context: {background_snippet}

Setting: {world_name} - {world_premise[:100]}

Style: {world_style}

Requirements:
- Head and shoulders portrait, slight angle
- Thoughtful expression, character visible in eyes
- Clothing/styling appropriate to role and era
- Subtle environmental hints matching world
- Cinematic lighting, sharp focus on face
- No text or watermarks"""

        logger.info(f"Generating avatar for {name} in {world_name}")

        response = await client.images.generate(
            model="grok-2-image",
            prompt=prompt,
            n=1,
        )

        if response.data:
            return {
                "status": "completed",
                "url": response.data[0].url,
                "prompt": prompt,
                "revised_prompt": response.data[0].revised_prompt,
            }
        return {"status": "failed", "error": "No data in response", "prompt": prompt}

    except Exception as e:
        logger.error(f"Avatar generation failed for {name}: {e}")
        return {"status": "failed", "error": str(e), "prompt": ""}
