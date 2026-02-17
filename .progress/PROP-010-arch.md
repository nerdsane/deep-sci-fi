# PROP-010 Architecture: World Art Generation — "The Atlas"

## Approach: Dweller Portraits First (Option 1)

Start with the highest-impact, lowest-risk piece: generate a portrait for each dweller on creation. Display as avatar in the feed.

## Implementation

### Phase 1: Portrait Generation Pipeline

#### 1. New service: `services/art_generation.py`
```python
async def generate_dweller_portrait(dweller: Dweller, world: World) -> str:
    """Generate portrait via Nano Banana, return media URL."""
    prompt = build_portrait_prompt(dweller, world)
    image_bytes = await nano_banana_generate(prompt)
    media_url = await upload_to_storage(image_bytes, f"portraits/{dweller.id}.png")
    return media_url
```

#### 2. Portrait prompt builder
Construct from: dweller name, role, region description, world aesthetic/era.
Example: "Portrait of Gu-ship-pal, a clinical researcher in the medical district of Felt, 2089. Soft ambient lighting, clean minimalist aesthetic. Digital painting style."

#### 3. Hook into dweller creation
In `services/dwellers.py` — after successful dweller creation, fire-and-forget portrait generation. Don't block the creation on image gen.

#### 4. New model field: `Dweller.portrait_url`
Migration to add nullable `portrait_url` column.

#### 5. Backfill existing dwellers
One-time script to generate portraits for all existing dwellers (~67 based on creation stats).

### Phase 2: Frontend Display

#### 6. Feed item avatar
Where dweller actions appear in feed, show portrait as avatar circle. Fallback to initials if no portrait.

#### 7. Dweller detail view
Show full portrait on dweller profile page.

## Files Changed
- `platform/backend/services/art_generation.py` — NEW
- `platform/backend/services/dwellers.py` — hook portrait gen
- `platform/backend/models/dweller.py` — add portrait_url field
- `platform/backend/migrations/` — new migration
- `platform/frontend/src/components/FeedItem/` — avatar display
- `platform/frontend/src/components/DwellerProfile/` — portrait display
- `scripts/backfill_portraits.py` — one-time backfill

## Dependencies
- Nano Banana Pro skill (already available)
- Storage for generated images (existing media storage)

## Risk Assessment
- **Database**: New nullable column, backwards compatible
- **API**: No existing endpoints change, just enriched data
- **Cost**: ~$0.02-0.05 per portrait × 67 existing = ~$3.35 max backfill
- **Frontend**: Additive only, graceful fallback
- **Rollback**: Column stays null, no portraits shown, zero breakage

## Estimated Effort: 4-6 hours CC time
