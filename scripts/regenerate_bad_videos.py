#!/usr/bin/env python3
"""Regenerate videos for stories with bad video prompts.

Finds stories where video_prompt contains artistic medium language or hand-focus,
rewrites the prompt using GPT-4o-mini, regenerates the video via Grok, and
updates the DB.

Usage:
    cd platform/backend
    source .venv/bin/activate
    python ../../scripts/regenerate_bad_videos.py [--dry-run] [--limit N]

Flags:
    --dry-run   Print rewritten prompts without generating videos
    --limit N   Process at most N stories (default: unlimited)
"""

import argparse
import asyncio
import logging
import os
import ssl
import sys
import uuid
from pathlib import Path

from openai import OpenAI
from sqlalchemy import create_engine, text

# Allow importing from the backend (media.generator, storage.r2, etc.)
backend_dir = Path(__file__).parent.parent / "platform" / "backend"
sys.path.insert(0, str(backend_dir))

# Load .env from platform/
from dotenv import load_dotenv  # noqa: E402
env_path = Path(__file__).parent.parent / "platform" / ".env"
load_dotenv(env_path)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DATABASE_URL = os.environ["DATABASE_URL"]

# Keyword patterns that indicate a bad prompt (case-insensitive substrings)
BAD_PATTERNS = [
    "watercolor",
    "painting of",
    "ink wash",
    "sketch of",
    "illustration of",
    "pencil sketch",
    "pencil drawing",
    "oil painting",
    "anime",
    "manga",
    "cartoon",
    "comic book",
]

REWRITE_SYSTEM_PROMPT = """Rewrite this video prompt for a photorealistic AI video generator.
Rules:
- Remove ALL artistic medium language (watercolor, painting, illustration, ink, sketch)
- Remove close-ups of hands. If the scene involves hands doing something,
  reframe to show the person/action from a wider angle instead.
- Replace "handmade" with "custom-built" or "improvised" where appropriate
- Keep the scene, mood, setting, and characters identical
- Use cinematic language: camera angles, lighting, depth of field, tracking shots
- Keep it under 200 words
Output ONLY the rewritten prompt, nothing else."""


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def make_engine():
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    return create_engine(
        DATABASE_URL,
        connect_args={"ssl": ssl_ctx, "statement_cache_size": 0},
        pool_pre_ping=True,
        pool_size=1,
        max_overflow=0,
    )


def find_bad_stories(conn, limit: int | None) -> list[dict]:
    """Return stories whose video_prompt matches any bad pattern."""
    where_clauses = " OR ".join(
        f"LOWER(video_prompt) LIKE '%{p.lower()}%'" for p in BAD_PATTERNS
    )
    query = text(f"""
        SELECT id, title, video_prompt, video_url
        FROM stories
        WHERE video_prompt IS NOT NULL
          AND ({where_clauses})
        ORDER BY created_at DESC
        {f'LIMIT {limit}' if limit else ''}
    """)
    rows = conn.execute(query).fetchall()
    return [dict(r._mapping) for r in rows]


def update_story_video(conn, story_id: str, video_url: str, new_prompt: str) -> None:
    conn.execute(
        text("""
            UPDATE stories
            SET video_url = :video_url,
                video_prompt = :video_prompt
            WHERE id = :id
        """),
        {"video_url": video_url, "video_prompt": new_prompt, "id": story_id},
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Prompt rewriting
# ---------------------------------------------------------------------------

def rewrite_prompt(client: OpenAI, original_prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
            {"role": "user", "content": original_prompt},
        ],
        max_tokens=300,
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def process_story(story: dict, dry_run: bool, openai_client: OpenAI, engine) -> None:
    story_id = str(story["id"])
    title = story["title"]
    original_prompt = story["video_prompt"]

    logger.info(f"\n{'='*60}")
    logger.info(f"Story: {title} ({story_id})")
    logger.info(f"Original prompt:\n  {original_prompt}")

    rewritten = rewrite_prompt(openai_client, original_prompt)
    logger.info(f"Rewritten prompt:\n  {rewritten}")

    if dry_run:
        logger.info("[DRY RUN] Skipping video generation and DB update.")
        return

    # Import here so dry-run doesn't require all env vars to be set
    from media.generator import generate_video  # noqa: PLC0415
    from storage.r2 import upload_media  # noqa: PLC0415

    logger.info("Generating video via Grok...")
    video_bytes = await generate_video(rewritten)

    key = f"media/story/{story_id}/video/{uuid.uuid4()}.mp4"
    logger.info(f"Uploading to R2: {key}")
    video_url = upload_media(video_bytes, key, "video/mp4")
    logger.info(f"Uploaded: {video_url}")

    with engine.connect() as conn:
        update_story_video(conn, story_id, video_url, rewritten)
    logger.info(f"DB updated for story {story_id}")


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print rewrites without generating")
    parser.add_argument("--limit", type=int, default=None, help="Max stories to process")
    args = parser.parse_args()

    openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    engine = make_engine()
    with engine.connect() as conn:
        stories = find_bad_stories(conn, args.limit)

    logger.info(f"Found {len(stories)} stories with bad video prompts.")
    if not stories:
        logger.info("Nothing to do.")
        return

    for story in stories:
        try:
            await process_story(story, dry_run=args.dry_run, openai_client=openai_client, engine=engine)
        except Exception as e:
            logger.error(f"Failed for story {story['id']}: {e}", exc_info=True)

    logger.info("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
