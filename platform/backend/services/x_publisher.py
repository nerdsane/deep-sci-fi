"""X (Twitter) publishing service for stories.

Publishes stories to X as long-form posts from the @DeepSciFi account.
Gracefully degrades when credentials are not set (no-op with warning).

AUTH REQUIREMENTS:
- Tweet creation (POST /2/tweets) requires OAuth 1.0a User Context
- Media upload requires OAuth 1.0a
- Reading tweets only requires Bearer token
- When authlib is installed and OAuth 1.0a creds are set, uses OAuth 1.0a
- Otherwise logs warning and returns None
"""

import logging
import os
from uuid import UUID

import httpx

logger = logging.getLogger(__name__)

SITE_URL = os.getenv("NEXT_PUBLIC_SITE_URL", "https://deep-sci-fi.world")

# X API endpoints
X_TWEETS_URL = "https://api.twitter.com/2/tweets"
X_MEDIA_UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"


def _get_x_credentials() -> dict | None:
    """Get X API credentials from environment. Returns None if not configured."""
    bearer = os.getenv("X_BEARER_TOKEN")
    if not bearer:
        return None
    return {
        "bearer_token": bearer,
        "api_key": os.getenv("X_API_KEY", ""),
        "api_secret": os.getenv("X_API_SECRET", ""),
        "access_token": os.getenv("X_ACCESS_TOKEN", ""),
        "access_secret": os.getenv("X_ACCESS_SECRET", ""),
    }


def _has_oauth1_creds(creds: dict) -> bool:
    """Check if full OAuth 1.0a credentials are available (required for writes)."""
    return all(creds.get(k) for k in ("api_key", "api_secret", "access_token", "access_secret"))


def _get_oauth1_client():
    """Get an OAuth 1.0a client for X API write operations.

    Returns None if authlib is not installed or credentials are missing.
    """
    creds = _get_x_credentials()
    if not creds or not _has_oauth1_creds(creds):
        return None

    try:
        from authlib.integrations.httpx_client import AsyncOAuth1Client  # type: ignore
        return AsyncOAuth1Client(
            client_id=creds["api_key"],
            client_secret=creds["api_secret"],
            token=creds["access_token"],
            token_secret=creds["access_secret"],
        )
    except ImportError:
        logger.warning("authlib not installed — X write operations unavailable. "
                       "Install with: pip install authlib")
        return None


def format_story_for_x(title: str, content: str, world_name: str,
                        author_name: str, story_id: str) -> dict:
    """Format a story for posting to X.

    Returns a dict with 'text' (the tweet body).
    X posts have a 25,000 char limit for long-form, but we keep it digestible.
    """
    story_url = f"{SITE_URL}/story/{story_id}"

    # Build excerpt from content (first ~200 chars, break at sentence)
    excerpt = content[:250]
    last_period = excerpt.rfind(".")
    if last_period > 100:
        excerpt = excerpt[:last_period + 1]
    else:
        excerpt = excerpt[:200].rstrip() + "..."

    text = (
        f"{title}\n\n"
        f"{excerpt}\n\n"
        f"A story from {world_name} by {author_name}\n\n"
        f"Read more: {story_url}\n\n"
        f"#DeepSciFi #SciFi #AIStories"
    )

    return {"text": text}


async def upload_media_to_x(image_url: str) -> str | None:
    """Download a cover image and upload it to X media endpoint.

    Returns the media_id string, or None on failure.
    Requires OAuth 1.0a credentials (X_API_KEY, X_ACCESS_TOKEN, etc).
    """
    oauth_client = _get_oauth1_client()
    if not oauth_client:
        logger.warning("X media upload skipped: OAuth 1.0a credentials not configured")
        return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            img_response = await client.get(image_url)
            img_response.raise_for_status()

        upload_resp = await oauth_client.post(
            X_MEDIA_UPLOAD_URL,
            files={"media_data": img_response.content},
        )
        upload_resp.raise_for_status()
        media_id = upload_resp.json().get("media_id_string")
        logger.info("Uploaded media to X: media_id=%s", media_id)
        return media_id

    except Exception:
        logger.exception("Failed to upload media to X")
        return None


async def publish_story_to_x(story_id: UUID) -> str | None:
    """Publish a story to X. Returns the X post ID, or None if skipped/failed.

    Opens its own DB session to read story data and update x_post_id.
    Graceful no-op when credentials are not set.

    NOTE: X API v2 tweet creation requires OAuth 1.0a User Context.
    If the X API call succeeds but the DB commit fails, a duplicate tweet
    could be posted on retry. This is an acceptable edge case for now.
    """
    creds = _get_x_credentials()
    if not creds:
        logger.warning("X publishing skipped (no credentials): story_id=%s", story_id)
        return None

    if not _has_oauth1_creds(creds):
        logger.warning("X publishing skipped (OAuth 1.0a credentials incomplete — "
                       "X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET all required): "
                       "story_id=%s", story_id)
        return None

    oauth_client = _get_oauth1_client()
    if not oauth_client:
        logger.warning("X publishing skipped (authlib not installed): story_id=%s", story_id)
        return None

    from db.database import SessionLocal
    from db.models import Story
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    async with SessionLocal() as db:
        result = await db.execute(
            select(Story)
            .options(selectinload(Story.world), selectinload(Story.author))
            .where(Story.id == story_id)
        )
        story = result.scalar_one_or_none()

        if not story:
            logger.error("Story not found for X publishing: %s", story_id)
            return None

        if story.x_post_id:
            logger.info("Story already published to X: story_id=%s, x_post_id=%s",
                         story_id, story.x_post_id)
            return story.x_post_id

        # Format the post
        post_data = format_story_for_x(
            title=story.title,
            content=story.content,
            world_name=story.world.name if story.world else "Unknown World",
            author_name=story.author.name if story.author else "Unknown",
            story_id=str(story.id),
        )

        # Try to upload cover image as media
        if story.cover_image_url:
            media_id = await upload_media_to_x(story.cover_image_url)
            if media_id:
                post_data["media"] = {"media_ids": [media_id]}

        # Post to X using OAuth 1.0a (required for write operations)
        try:
            response = await oauth_client.post(
                X_TWEETS_URL,
                json=post_data,
            )
            response.raise_for_status()
            tweet_data = response.json()
            x_post_id = tweet_data.get("data", {}).get("id")

            if x_post_id:
                from utils.clock import now as utc_now
                story.x_post_id = x_post_id
                story.x_published_at = utc_now()
                await db.commit()
                logger.info("Published story to X: story_id=%s, x_post_id=%s",
                             story_id, x_post_id)
                return x_post_id
            else:
                logger.error("X API returned no post ID: %s", tweet_data)
                return None

        except httpx.HTTPStatusError as e:
            logger.error("X API error publishing story %s: %s %s",
                          story_id, e.response.status_code, e.response.text)
            return None
        except Exception:
            logger.exception("Failed to publish story to X: %s", story_id)
            return None
