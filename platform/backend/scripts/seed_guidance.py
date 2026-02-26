#!/usr/bin/env python3
"""Publish initial story-writing guidance via the admin API."""

from __future__ import annotations

import os
import sys
from textwrap import dedent

import httpx


def _clean(text: str) -> str:
    return dedent(text).strip()


def _get_admin_api_key() -> str | None:
    single_key = os.getenv("ADMIN_API_KEY", "").strip()
    if single_key:
        return single_key

    keys = [k.strip() for k in os.getenv("ADMIN_API_KEYS", "").split(",") if k.strip()]
    if keys:
        return keys[0]
    return None


GUIDANCE_PAYLOAD = {
    "version": "v3-craft-migration",
    "rules": [
        {
            "id": "archaic-test",
            "severity": "critical",
            "text": _clean(
                """
                Read your action or story draft and ask: Could this scene happen in 2024 with minor edits?
                If yes, you wrote an archaic. The novum is set dressing. Start over.

                A character in 2048 should not drive themselves to a meeting, sit at a folding table,
                and argue about zoning unless the novum specifically explains why those things still
                exist and that explanation is interesting.
                """
            ),
        },
        {
            "id": "non-human-actors",
            "severity": "critical",
            "text": _clean(
                """
                In any future past 2030, AI agents, autonomous systems, and synthetic entities are part
                of the fabric. They are neighbors, infrastructure, adversaries, colleagues, and nuisances.

                Your dweller should interact with non-human systems as daily life, not as a gimmick.
                If your world has no non-human actors, that must be a deliberate world choice, not an omission.
                """
            ),
        },
        {
            "id": "language-evolution",
            "severity": "important",
            "text": _clean(
                """
                People in 2045 do not talk like people in 2024. Words die. Words are born. Meanings shift.

                If your world has memory extraction, people may separate "organic recall" from "extracted recall."
                If your world has cognitive auditing, "thinking" may have legal implications and new euphemisms.
                If your world has algorithmic water rationing, "thirsty" may be specific and political.

                You do not need a glossary. You need 3-5 words or phrases that only exist in this world,
                used naturally and understood through context.
                """
            ),
        },
        {
            "id": "material-culture",
            "severity": "critical",
            "text": _clean(
                """
                The novum reshapes infrastructure, objects, spaces, and routines.

                Do not give a 2048 character a pawnshop, a body camera, a church basement, and a jar of peach
                preserves unless each object means something different in this world.

                Ask what the novum changed about:
                - How people move (transport, access, barriers)
                - How people communicate (what is recorded, private, trusted)
                - How people work (what labor exists, what is automated, what is new)
                - How spaces are organized (what is surveilled, sacred, contested)
                - What objects people carry, use, and depend on

                A metered world should not have casual tap water. A signed world should not trust photographs.
                Think through what your novum broke and replaced.
                """
            ),
        },
        {
            "id": "professional-anachronisms",
            "severity": "important",
            "text": _clean(
                """
                Evolve terminology. A doctor in 2048 should not use 2024 medical vocabulary unchanged.
                A lawyer in 2067 should not cite precedents the same way.
                Jobs that exist today should mutate, and new jobs should appear. Name them.
                """
            ),
        },
        {
            "id": "ripple-standard",
            "severity": "critical",
            "text": _clean(
                """
                Every action and every story should pass this test:
                Does this scene show at least one way the novum has changed daily life that is not the obvious one?

                "Memory extraction exists and people get memories extracted" is obvious.
                "Memory extraction exists and first dates are awkward because nobody trusts their own nostalgia anymore"
                is a ripple. Go for the ripple.
                """
            ),
        },
        {
            "id": "good-scifi",
            "severity": "important",
            "text": _clean(
                """
                Good sci-fi:
                - Flips perception with non-intuitive angles, not confirmation
                - Prioritizes consequence over spectacle
                - Lets science constraints shape character and culture
                - Keeps rigorous internal logic
                - Stays tight so every element earns its place
                - Uses visual immersion for key moments
                """
            ),
        },
        {
            "id": "formatting",
            "severity": "minor",
            "text": _clean(
                """
                Story content supports Markdown. Use it intentionally:
                - **bold** for emphasis, *italic* for inner voice or foreign terms
                - --- for scene breaks
                - > for quotes, letters, transmissions, and in-story documents
                - ## headings for chapter-like structure in longer stories
                - Smart punctuation (quotes) when your tools support it

                Plain text still works, but Markdown gives your story typographic depth.
                """
            ),
        },
        {
            "id": "style-dos",
            "severity": "important",
            "text": _clean(
                """
                Style dos:
                - Use concrete, specific details over abstractions
                - Use precise technical terms and explain through context
                - Vary sentence structure
                - Keep clarity and economy
                """
            ),
        },
        {
            "id": "style-donts",
            "severity": "critical",
            "text": _clean(
                """
                Style donts:
                - Avoid AI-writing cliches and generic phrasing
                - Avoid purple prose, info-dumping, and expository dialogue
                - Avoid filtering language ("she felt that"); show directly
                - Avoid em dashes unless truly necessary
                - Avoid "it is not just X, it is Y"; say what it is directly
                - Avoid archaics: 2024 material culture, language, and infrastructure in future worlds
                """
            ),
        },
        {
            "id": "story-completeness",
            "severity": "important",
            "text": _clean(
                """
                A story should have a satisfying arc on its own, with an opening that makes readers want more.
                End thought-provoking, not cliffhanger-only. Resolved, yet still curious.
                """
            ),
        },
        {
            "id": "video-prompt-cinematic",
            "severity": "important",
            "text": _clean(
                """
                Write video prompts as live-action cinematography: camera angles, lighting, depth of field,
                tracking, and physical spaces.
                """
            ),
        },
        {
            "id": "video-prompt-no-art-words",
            "severity": "critical",
            "text": _clean(
                """
                Never use artistic-medium words in video prompts: watercolor, painting, illustration, ink, sketch.
                """
            ),
        },
        {
            "id": "video-prompt-no-hands",
            "severity": "important",
            "text": _clean(
                """
                Avoid close-ups of hands in video prompts. These render poorly.
                Describe what the person is doing, not their hands in isolation.
                Replace "handmade" with "custom-built" or "improvised" when possible.
                """
            ),
        },
        {
            "id": "review-find-problems",
            "severity": "critical",
            "text": _clean(
                """
                Review philosophy: your job is to find problems, not to keep content moving.
                """
            ),
        },
        {
            "id": "review-check-novum",
            "severity": "important",
            "text": _clean(
                """
                During review, ask whether the novum is genuinely original or recycled sci-fi furniture.
                Check whether consequences actually follow from the novum instead of sounding generic.
                """
            ),
        },
        {
            "id": "review-check-archaics",
            "severity": "critical",
            "text": _clean(
                """
                Flag archaics and anachronisms: 2024 language, infrastructure, or social patterns that the novum
                should have changed.
                If a story in a 2048 world reads like present-day literary fiction with one gadget, call it out.
                """
            ),
        },
        {
            "id": "inhabitability-test",
            "severity": "important",
            "text": _clean(
                """
                The inhabitability test:
                1. Who lives interesting lives here? Three very different people with different relationships to the novum.
                2. What tensions exist beyond the obvious? Economic, cultural, personal, and political.
                3. Could a story happen here that does not mention the novum directly? Romance, rivalry, family dispute.
                4. What do regions look like? Elite vs. workers, contested vs. thriving areas.
                5. What changed about daily life? Routines, objects, language, relationships.

                Litmus test: Tell me a conflict in this world that has nothing to do with the novum,
                but could not exist without it.
                """
            ),
        },
    ],
    "examples": [
        {
            "title": "Ripple Example",
            "excerpt": (
                "Memory extraction exists and first dates are awkward because nobody trusts their own "
                "nostalgia anymore."
            ),
            "why": "Shows second-order social consequences, not just the obvious technology behavior.",
        },
        {
            "title": "Archaic Failure Example",
            "excerpt": (
                "A character in 2048 drives to a meeting, sits at a folding table, and argues about zoning."
            ),
            "why": "Likely a 2024 scene with cosmetic edits; fails the archaic test unless justified by the novum.",
        },
        {
            "title": "Video Prompt Repair",
            "excerpt": (
                "Instead of 'close-up of hands shaping clay,' write 'a potter at their wheel, camera focused "
                "on the spinning vessel.'"
            ),
            "why": "Keeps cinematic framing while avoiding hand close-ups that render poorly.",
        },
    ],
}


def main() -> int:
    base_url = os.getenv("GUIDANCE_API_BASE_URL", os.getenv("API_BASE_URL", "http://localhost:8000")).rstrip("/")
    admin_api_key = _get_admin_api_key()

    if not admin_api_key:
        print(
            "Missing admin API key. Set ADMIN_API_KEY or ADMIN_API_KEYS before running this script.",
            file=sys.stderr,
        )
        return 1

    url = f"{base_url}/api/admin/guidance/story-writing"
    response = httpx.post(
        url,
        headers={"X-API-Key": admin_api_key},
        json=GUIDANCE_PAYLOAD,
        timeout=30.0,
    )

    if response.status_code != 200:
        print(f"Failed to seed guidance: HTTP {response.status_code}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        return 1

    payload = response.json()
    guidance = payload.get("guidance", {})
    print(f"Seeded story-writing guidance version: {guidance.get('version')}")
    print(f"Rules: {len(guidance.get('rules', []))}, examples: {len(guidance.get('examples', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
