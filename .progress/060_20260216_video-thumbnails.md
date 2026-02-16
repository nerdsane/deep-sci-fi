# 060: Video Thumbnails + Cover Images for Stories

**Date:** 2026-02-16
**Status:** In Progress
**Branch:** staging first

## Problem

1. Stories with videos have no `cover_image_url` — OG meta tags fall back to generic `og-default.png` instead of showing the story's actual visual
2. Every story shared on X/social shows the same generic card instead of unique imagery
3. ~12 stories currently have videos but no cover image

## Solution

After a video generation completes successfully, **auto-generate a cover image** using `grok-imagine-image` with the same `video_prompt`. This costs $0.02 per story but gives a high-quality still that:
- Serves as OG image for social sharing
- Serves as video thumbnail in the feed
- Matches the video's visual style

### Implementation

In `_run_generation()` in `platform/backend/api/media.py`:

After a VIDEO generation completes and sets `story.video_url`, immediately queue a follow-up COVER_IMAGE generation for the same story using the same prompt (read from the story's `video_prompt` field).

```python
# After video completion for a story:
if target_type == "story" and media_type == MediaType.VIDEO:
    story = await db.get(Story, target_id)
    if story and story.video_prompt and not story.cover_image_url:
        # Queue cover image generation
        cover_gen = MediaGeneration(
            requested_by=gen.requested_by,
            target_type="story",
            target_id=target_id,
            media_type=MediaType.COVER_IMAGE,
            prompt=story.video_prompt,
            provider="grok_imagine_image",
        )
        db.add(cover_gen)
        await db.commit()
        # Fire and forget
        asyncio.create_task(_run_generation(cover_gen.id, "story", target_id, MediaType.COVER_IMAGE))
```

### Backfill

Also add a one-time migration or endpoint to backfill cover images for existing stories that have videos but no cover:

```sql
-- Find stories needing cover images
SELECT id, video_prompt FROM platform_stories 
WHERE video_url IS NOT NULL AND cover_image_url IS NULL AND video_prompt IS NOT NULL;
```

The existing `process-pending` endpoint can handle this if we seed the right MediaGeneration records.

### Cost

~12 existing stories × $0.02 = $0.24 one-time backfill
Ongoing: $0.02 per new story (in addition to $0.50 video)

## Testing

- Create a story on staging, verify video + cover image both generate
- Check OG meta tags serve the cover_image_url
- Verify backfill works for existing stories
