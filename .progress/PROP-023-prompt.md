# PROP-023: Story Typography Fix + Video Prompt Sanitization + Regeneration

## Part 1: Typography Fix (frontend)

Fix story body text readability in `platform/components/story/StoryContent.tsx` and any related CSS:

1. **Line-height**: increase from current (~1.3) to `1.65` for story body text
2. **Paragraph spacing**: increase margin-bottom between paragraphs to `1.2em`
3. **Font size**: bump body text to `17px` (from ~15-16px)
4. **Consider switching story body to a proportional font** — keep monospace for metadata, nav, UI chrome. For the story prose itself, use a clean sans-serif or serif. If you use a proportional font, import it properly (e.g., Inter, Source Serif Pro, or similar from Google Fonts / next/font).
5. **Max line length**: ensure body text doesn't exceed `70ch` width

Test on both desktop (1280px) and mobile (375px). Take Rodney screenshots before and after.

### Rodney verification (MANDATORY)
```bash
rodney start
# BEFORE screenshots
rodney open "https://deep-sci-fi.world/stories/697d57a3-51ce-47d5-bd7f-e4f2965cd8e6"
rodney waitstable
rodney screenshot -w 1280 -h 1600 /tmp/prop023-typo-before-desktop.png
rodney open "https://deep-sci-fi.world/stories/697d57a3-51ce-47d5-bd7f-e4f2965cd8e6" -w 375
rodney waitstable
rodney screenshot -w 375 -h 812 /tmp/prop023-typo-before-mobile.png

# After your changes, deploy to staging, then:
rodney open "https://staging.deep-sci-fi.world/stories/697d57a3-51ce-47d5-bd7f-e4f2965cd8e6"
rodney waitstable
rodney screenshot -w 1280 -h 1600 /tmp/prop023-typo-after-desktop.png
rodney open "https://staging.deep-sci-fi.world/stories/697d57a3-51ce-47d5-bd7f-e4f2965cd8e6" -w 375
rodney waitstable
rodney screenshot -w 375 -h 812 /tmp/prop023-typo-after-mobile.png
```

## Part 2: Video Prompt Sanitization (backend)

In `platform/backend/media/generator.py`, add a prompt sanitization step BEFORE the style prefix:

```python
def sanitize_video_prompt(prompt: str) -> str:
    """Remove artistic medium language and hand-focus from video prompts.
    
    Artistic medium words cause Grok to generate anime/illustration style.
    Hand descriptions cause anatomical artifacts (Grok can't render hands well).
    """
    import re
    
    # Remove artistic medium phrases
    medium_patterns = [
        r'\bwatercolor\s+(painting|illustration)\s+of\b',
        r'\bwatercolor\b',
        r'\boil\s+painting\s+of\b',
        r'\bink\s+(wash|drawing|sketch)\s+of\b',
        r'\bpencil\s+(sketch|drawing)\s+of\b',
        r'\billustration\s+of\b',
        r'\bsketch\s+of\b',
        r'\bin\s+the\s+style\s+of\s+\w+\s+(painting|illustration|art)\b',
        r'\banime\b',
        r'\bmanga\b',
        r'\bcartoon\b',
        r'\bcomic\s+book\b',
    ]
    for pattern in medium_patterns:
        prompt = re.sub(pattern, '', prompt, flags=re.IGNORECASE)
    
    # Clean up double spaces from removals
    prompt = re.sub(r'\s+', ' ', prompt).strip()
    
    return prompt
```

Call `sanitize_video_prompt(prompt)` BEFORE prepending the style prefix in `generate_video()`.

## Part 3: Video Regeneration Script

Create `scripts/regenerate_bad_videos.py`:

1. Query all stories where `video_prompt` contains hand-related or artistic medium language:
   - Matches: `watercolor`, `painting of`, `ink wash`, `sketch of`, `illustration of`
   - OR: prompts where hands are the primary subject (use an LLM to classify)

2. For each story:
   a. Send the original `video_prompt` to OpenAI gpt-4o-mini with this system prompt:
   ```
   Rewrite this video prompt for a photorealistic AI video generator.
   Rules:
   - Remove ALL artistic medium language (watercolor, painting, illustration, ink, sketch)
   - Remove close-ups of hands. If the scene involves hands doing something, 
     reframe to show the person/action from a wider angle instead.
   - Replace "handmade" with "custom-built" or "improvised" where appropriate
   - Keep the scene, mood, setting, and characters identical
   - Use cinematic language: camera angles, lighting, depth of field
   - Keep it under 200 words
   Output ONLY the rewritten prompt, nothing else.
   ```
   b. Call `generate_video()` with the rewritten prompt (which will also get the style prefix)
   c. Upload to R2, update `video_url` in DB
   d. Log: original prompt → rewritten prompt → new video URL

3. Run in dry-run mode first (`--dry-run` flag) that prints rewrites without generating

**Database connection** — use this pattern for local Supabase access:
```python
import ssl
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE
# In SQLAlchemy: connect_args={'ssl': ssl_ctx, 'statement_cache_size': 0}
# In asyncpg: ssl=ssl_ctx, statement_cache_size=0
```

**Environment variables needed:**
- `DATABASE_URL` — Supabase pooler URL
- `XAI_API_KEY` — for Grok video generation  
- `OPENAI_API_KEY` — for prompt rewriting
- `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME` — for upload

The upload function is at `platform/backend/media/storage.py` → `upload_media()`. It is SYNC (not async). Do NOT await it.

## Part 4: Update skill.md

Add to the video prompt section of `platform/public/skill.md`:

```markdown
## Video Prompt Guidelines

When writing video_prompt for stories:
- Use CINEMATIC language: camera angles, lighting, depth of field, tracking shots
- NEVER use artistic medium words: "watercolor", "painting", "illustration", "ink", "sketch"
- AVOID close-ups of hands — video models render them poorly
  - Instead of "close-up of hands shaping clay" → "a potter at their wheel, camera focused on the spinning vessel"
  - Instead of "hands grip a hammer" → "a carpenter drives nails into a beam, sawdust catching the light"
- Replace "handmade" with "custom-built" or "improvised"
- Describe what the PERSON is doing, not what their hands are doing
```

## Showboat Documentation

```bash
uvx showboat init reports/PROP-023-complete.md "PROP-023: Typography + Video Prompt Sanitization"

# Typography before/after
uvx showboat image reports/PROP-023-complete.md /tmp/prop023-typo-before-desktop.png "Typography BEFORE — desktop"
uvx showboat image reports/PROP-023-complete.md /tmp/prop023-typo-after-desktop.png "Typography AFTER — desktop"
uvx showboat image reports/PROP-023-complete.md /tmp/prop023-typo-before-mobile.png "Typography BEFORE — mobile"
uvx showboat image reports/PROP-023-complete.md /tmp/prop023-typo-after-mobile.png "Typography AFTER — mobile"

# Sanitization test
uvx showboat exec reports/PROP-023-complete.md bash "cd platform/backend && python3 -c \"from media.generator import sanitize_video_prompt; print(sanitize_video_prompt('Watercolor painting of a woman with handmade instruments'))\""

# Dry-run of regeneration
uvx showboat exec reports/PROP-023-complete.md bash "cd platform/backend && python3 ../../scripts/regenerate_bad_videos.py --dry-run 2>&1 | head -40"

# Test results
uvx showboat exec reports/PROP-023-complete.md bash "cd platform/backend && python3 -m pytest tests/ -v 2>&1 | tail -30"
```

## What NOT to do
- Do NOT change the monospace font for navigation, metadata, timestamps, or UI elements — only story body prose
- Do NOT remove the style prefix from generate_video — the sanitization is an ADDITIONAL step before it
- Do NOT actually run the regeneration script — just create it. We'll run it manually after review.
- Do NOT change the story content or titles — only video prompts and typography CSS
