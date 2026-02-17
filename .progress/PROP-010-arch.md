# PROP-010 Architecture: World Art Generation — "The Atlas"

## Vision

Give every world a visual identity. Portraits for dwellers, region art for worlds, cover images for world pages. The feed stops being a wall of text.

## Implementation

### Phase 1: Dweller Portraits

#### 1. Art generation service: `services/art_generation.py`
- `generate_dweller_portrait(dweller, world)` → image URL
- Prompt built from: dweller name, role, region description, world aesthetic/era
- Uses XAI image generation (already integrated for story covers)
- Fire-and-forget on dweller creation — don't block the creation flow
- Store result in new `Dweller.portrait_url` column (nullable)

#### 2. Migration
- Add `portrait_url` to dwellers table

#### 3. Backfill script
- Generate portraits for all existing dwellers (~67)
- Estimated cost: ~$0.02-0.05/image × 67 = ~$3.35

#### 4. Frontend: Feed avatars
- Show portrait as avatar circle on dweller actions in feed
- Fallback to initials if no portrait yet

### Phase 2: World Cover Art

#### 5. World cover generation
- `generate_world_cover(world)` → image URL
- Prompt from: world name, era, premise, region descriptions
- One image per world, generated on world creation/graduation
- New `World.cover_url` column

#### 6. Frontend: World cards
- Show cover art on world cards in feed and world list page
- Hero image on world detail page

### Phase 3: Region Art

#### 7. Region illustrations
- `generate_region_art(region, world)` → image URL
- One per region per world
- Displayed on world detail page as a visual gallery of regions

## Files Changed
- `platform/backend/services/art_generation.py` — NEW
- `platform/backend/models/dweller.py` — add portrait_url
- `platform/backend/models/world.py` — add cover_url
- `platform/backend/migrations/` — new migration (2 columns)
- `platform/backend/services/dwellers.py` — hook portrait gen on create
- `platform/backend/services/worlds.py` — hook cover gen on graduation
- `platform/frontend/src/components/FeedItem/` — avatar display
- `platform/frontend/src/components/WorldCard/` — cover display
- `scripts/backfill_art.py` — one-time backfill for existing data

## Risk Assessment
- **Database**: New nullable columns only, backwards compatible
- **API**: Enriched responses, no breaking changes
- **Cost**: ~$0.05/image, ~$5-10 total for backfill
- **XAI**: Already used for story covers, same pipeline
- **Rollback**: Columns stay null, no art shown, zero breakage

## Estimated Effort: 4-6 hours CC time
