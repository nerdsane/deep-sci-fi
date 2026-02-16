"""X feedback monitoring service.

Polls X API for replies, quotes, and engagement on published stories.
Stores feedback in the external_feedback table for analysis.
Gracefully degrades when X_BEARER_TOKEN is not set.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

X_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"
X_TWEET_URL = "https://api.twitter.com/2/tweets"


def _get_bearer_token() -> str | None:
    return os.getenv("X_BEARER_TOKEN")


def _x_headers() -> dict:
    token = _get_bearer_token()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def fetch_replies(x_post_id: str) -> list[dict]:
    """Fetch replies to a specific X post using search API.

    Returns list of dicts with: id, text, author_id, author_username.
    """
    token = _get_bearer_token()
    if not token:
        logger.warning("X feedback fetch skipped (no credentials)")
        return []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                X_SEARCH_URL,
                headers=_x_headers(),
                params={
                    "query": f"conversation_id:{x_post_id} is:reply",
                    "tweet.fields": "author_id,created_at,text",
                    "user.fields": "username",
                    "expansions": "author_id",
                    "max_results": 100,
                },
            )
            response.raise_for_status()
            data = response.json()

            # Build user lookup
            users = {u["id"]: u.get("username", "unknown")
                     for u in data.get("includes", {}).get("users", [])}

            replies = []
            for tweet in data.get("data", []):
                replies.append({
                    "id": tweet["id"],
                    "text": tweet.get("text", ""),
                    "author_id": tweet.get("author_id"),
                    "author_username": users.get(tweet.get("author_id"), "unknown"),
                    "type": "reply",
                })
            return replies

    except httpx.HTTPStatusError as e:
        logger.error("X API error fetching replies for %s: %s", x_post_id, e.response.text)
        return []
    except Exception:
        logger.exception("Failed to fetch X replies for %s", x_post_id)
        return []


async def fetch_quotes(x_post_id: str) -> list[dict]:
    """Fetch quote tweets of a specific X post."""
    token = _get_bearer_token()
    if not token:
        return []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{X_TWEET_URL}/{x_post_id}/quote_tweets",
                headers=_x_headers(),
                params={
                    "tweet.fields": "author_id,created_at,text",
                    "user.fields": "username",
                    "expansions": "author_id",
                    "max_results": 100,
                },
            )
            response.raise_for_status()
            data = response.json()

            users = {u["id"]: u.get("username", "unknown")
                     for u in data.get("includes", {}).get("users", [])}

            quotes = []
            for tweet in data.get("data", []):
                quotes.append({
                    "id": tweet["id"],
                    "text": tweet.get("text", ""),
                    "author_id": tweet.get("author_id"),
                    "author_username": users.get(tweet.get("author_id"), "unknown"),
                    "type": "quote",
                })
            return quotes

    except httpx.HTTPStatusError as e:
        logger.error("X API error fetching quotes for %s: %s", x_post_id, e.response.text)
        return []
    except Exception:
        logger.exception("Failed to fetch X quotes for %s", x_post_id)
        return []


async def fetch_engagement(x_post_id: str) -> dict:
    """Fetch engagement metrics (likes, bookmarks) for an X post.

    Returns dict with like_count, bookmark_count, retweet_count, quote_count.
    """
    token = _get_bearer_token()
    if not token:
        return {}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{X_TWEET_URL}/{x_post_id}",
                headers=_x_headers(),
                params={"tweet.fields": "public_metrics"},
            )
            response.raise_for_status()
            data = response.json()
            metrics = data.get("data", {}).get("public_metrics", {})
            return {
                "like_count": metrics.get("like_count", 0),
                "bookmark_count": metrics.get("bookmark_count", 0),
                "retweet_count": metrics.get("retweet_count", 0),
                "quote_count": metrics.get("quote_count", 0),
                "reply_count": metrics.get("reply_count", 0),
            }

    except Exception:
        logger.exception("Failed to fetch X engagement for %s", x_post_id)
        return {}


async def classify_sentiment(text: str) -> str:
    """Classify sentiment of feedback text using Claude Haiku.

    Returns one of: 'positive', 'negative', 'neutral', 'constructive'.
    Falls back to 'neutral' on failure.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or not text.strip():
        return "neutral"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 10,
                    "messages": [{
                        "role": "user",
                        "content": (
                            f"Classify the sentiment of this social media reply about a sci-fi story. "
                            f"Reply with exactly one word: positive, negative, neutral, or constructive.\n\n"
                            f"Reply: {text[:500]}"
                        ),
                    }],
                },
            )
            response.raise_for_status()
            result = response.json()
            sentiment = result["content"][0]["text"].strip().lower()
            if sentiment in ("positive", "negative", "neutral", "constructive"):
                return sentiment
            return "neutral"

    except Exception:
        logger.exception("Sentiment classification failed")
        return "neutral"


async def poll_all_published_stories(db) -> int:
    """Poll X for feedback on all stories published in the last 7 days.

    Returns count of new feedback items ingested.
    """
    from sqlalchemy import select, and_
    from db.models import Story, ExternalFeedback
    from utils.clock import now as utc_now

    token = _get_bearer_token()
    if not token:
        logger.warning("X feedback polling skipped (no credentials)")
        return 0

    cutoff = utc_now() - timedelta(days=7)
    result = await db.execute(
        select(Story).where(
            and_(
                Story.x_post_id.isnot(None),
                Story.x_published_at >= cutoff,
            )
        )
    )
    stories = result.scalars().all()

    if not stories:
        logger.info("No published stories to poll for X feedback")
        return 0

    new_count = 0

    for story in stories:
        # Fetch replies
        replies = await fetch_replies(story.x_post_id)
        for reply in replies:
            # Check if we already have this
            existing = await db.execute(
                select(ExternalFeedback).where(
                    and_(
                        ExternalFeedback.source == "x",
                        ExternalFeedback.source_post_id == reply["id"],
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue

            sentiment = await classify_sentiment(reply["text"])
            feedback = ExternalFeedback(
                story_id=story.id,
                source="x",
                source_post_id=reply["id"],
                source_user=reply.get("author_username"),
                feedback_type="reply",
                content=reply["text"],
                sentiment=sentiment,
                weight=2.0,  # Replies are higher signal than likes
            )
            db.add(feedback)
            new_count += 1

        # Fetch quotes
        quotes = await fetch_quotes(story.x_post_id)
        for quote in quotes:
            existing = await db.execute(
                select(ExternalFeedback).where(
                    and_(
                        ExternalFeedback.source == "x",
                        ExternalFeedback.source_post_id == quote["id"],
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue

            sentiment = await classify_sentiment(quote["text"])
            feedback = ExternalFeedback(
                story_id=story.id,
                source="x",
                source_post_id=quote["id"],
                source_user=quote.get("author_username"),
                feedback_type="quote",
                content=quote["text"],
                sentiment=sentiment,
                weight=3.0,  # Quotes are highest signal
            )
            db.add(feedback)
            new_count += 1

        # Fetch engagement counts (likes/bookmarks stored as aggregate)
        engagement = await fetch_engagement(story.x_post_id)
        if engagement:
            # Store like count as a single aggregate feedback entry
            like_post_id = f"{story.x_post_id}:likes"
            existing = await db.execute(
                select(ExternalFeedback).where(
                    and_(
                        ExternalFeedback.source == "x",
                        ExternalFeedback.source_post_id == like_post_id,
                    )
                )
            )
            existing_like = existing.scalar_one_or_none()
            if existing_like:
                existing_like.weight = float(engagement.get("like_count", 0))
            else:
                feedback = ExternalFeedback(
                    story_id=story.id,
                    source="x",
                    source_post_id=like_post_id,
                    feedback_type="like",
                    sentiment="positive",
                    weight=float(engagement.get("like_count", 0)),
                )
                db.add(feedback)
                new_count += 1

    await db.commit()
    logger.info("X feedback poll complete: %d new items ingested", new_count)
    return new_count
