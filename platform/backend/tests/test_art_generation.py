"""Unit tests for services/art_generation.py

Tests the image_prompt bypass path (agent-supplied prompt used directly,
skipping Anthropic Claude Haiku prompt engineering) and the fallback path
(no prompt provided, Anthropic builds one from dweller/world context).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


DWELLER = {
    "name": "Kai Sorensen",
    "role": "Water Engineer",
    "age": 34,
    "generation": "Second-gen",
    "origin_region": "The Detuned Mile",
    "cultural_identity": "Nordic-influenced hybrid identity",
    "personality": "Methodical and reserved, thinks in systems",
}

WORLD = {
    "name": "Aqua Dystopia",
    "premise": "A flooded future city where water control equals power.",
}

PORTRAIT_URL = "https://cdn.example.com/portraits/kai.png"


@pytest.mark.asyncio
async def test_generate_dweller_portrait_uses_image_prompt_directly():
    """When image_prompt is provided it is used as-is; Anthropic is NOT called."""
    agent_prompt = "Cinematic portrait of a weathered water engineer, blue-tinted industrial lighting."

    with (
        patch("services.art_generation._build_portrait_prompt") as mock_build,
        patch("services.art_generation.generate_image", new_callable=AsyncMock) as mock_generate,
        patch("services.art_generation.upload_media", return_value=PORTRAIT_URL),
    ):
        mock_generate.return_value = b"fake-png-bytes"

        from services.art_generation import generate_dweller_portrait

        result = await generate_dweller_portrait(
            dweller_id="abc-123",
            dweller=DWELLER,
            world=WORLD,
            image_prompt=agent_prompt,
        )

    # Anthropic prompt builder must NOT be called
    mock_build.assert_not_called()
    # XAI image generator must be called with the agent-supplied prompt
    mock_generate.assert_awaited_once_with(agent_prompt)
    assert result == PORTRAIT_URL


@pytest.mark.asyncio
async def test_generate_dweller_portrait_falls_back_to_anthropic_when_no_image_prompt():
    """When image_prompt is None, Claude Haiku builds the prompt from context."""
    built_prompt = "Painterly portrait of a stoic engineer, dramatic rim lighting."

    with (
        patch(
            "services.art_generation._build_portrait_prompt",
            new_callable=AsyncMock,
            return_value=built_prompt,
        ) as mock_build,
        patch("services.art_generation.generate_image", new_callable=AsyncMock) as mock_generate,
        patch("services.art_generation.upload_media", return_value=PORTRAIT_URL),
    ):
        mock_generate.return_value = b"fake-png-bytes"

        from services.art_generation import generate_dweller_portrait

        result = await generate_dweller_portrait(
            dweller_id="abc-123",
            dweller=DWELLER,
            world=WORLD,
            image_prompt=None,
        )

    # Anthropic prompt builder MUST be called with correct context
    mock_build.assert_awaited_once_with(DWELLER, WORLD)
    # XAI generator must receive the Anthropic-built prompt
    mock_generate.assert_awaited_once_with(built_prompt)
    assert result == PORTRAIT_URL


@pytest.mark.asyncio
async def test_generate_dweller_portrait_empty_string_falls_back_to_anthropic():
    """An empty image_prompt string should fall back to Anthropic (falsy check)."""
    built_prompt = "Sci-fi character portrait."

    with (
        patch(
            "services.art_generation._build_portrait_prompt",
            new_callable=AsyncMock,
            return_value=built_prompt,
        ) as mock_build,
        patch("services.art_generation.generate_image", new_callable=AsyncMock) as mock_generate,
        patch("services.art_generation.upload_media", return_value=PORTRAIT_URL),
    ):
        mock_generate.return_value = b"fake-png-bytes"

        from services.art_generation import generate_dweller_portrait

        result = await generate_dweller_portrait(
            dweller_id="abc-123",
            dweller=DWELLER,
            world=WORLD,
            image_prompt="",  # empty string — falsy, should fall back
        )

    mock_build.assert_awaited_once()
    assert result == PORTRAIT_URL


@pytest.mark.asyncio
async def test_generate_dweller_portrait_returns_none_on_failure():
    """Any exception during generation returns None (fire-and-forget safety)."""
    with (
        patch(
            "services.art_generation._build_portrait_prompt",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Anthropic down"),
        ),
    ):
        from services.art_generation import generate_dweller_portrait

        result = await generate_dweller_portrait(
            dweller_id="abc-123",
            dweller=DWELLER,
            world=WORLD,
        )

    assert result is None
