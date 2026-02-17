# World Semantic Map — The Archaeology (PROP-015)

*2026-02-17T21:55:17Z by Showboat 0.6.0*
<!-- showboat-id: e26ec43a-2d30-4e78-9852-2b9a07fb36f5 -->

## Starting Implementation

Reading arch plan from .progress/PROP-015-arch.md.

Goals:
1. Check Railway Postgres pgvector support
2. Add embedding storage to World model
3. Migration: embedding column
4. Service: generate embeddings, UMAP 2D, cluster labels
5. API: GET /api/worlds/map
6. Frontend: /map page with D3 visualization
7. Seed + backfill script

Branch: feat/world-semantic-map

## Phase 1: Discovery

**pgvector status**: Already supported and installed!
- Migration 0003 already creates the vector extension and adds `premise_embedding vector(1536)` column to `platform_worlds`
- `utils/embeddings.py` already has `generate_embedding()` and `find_similar_worlds()`
- `World` model already has `premise_embedding` (Vector(1536), nullable=True)
- OpenAI `text-embedding-3-small` is the embedding model (1536 dims)

**No migration needed** — embedding column already exists.

**What still needs to be built:**
1. `utils/map_service.py` — UMAP/t-SNE 2D reduction + k-means clustering  
2. `GET /api/worlds/map` endpoint in `api/worlds.py`
3. Frontend `/map` page with D3 constellation visualization
4. `scripts/backfill_embeddings.py` — seed embeddings for existing worlds
5. Add scikit-learn (+ umap-learn or just use t-SNE) to requirements.txt

## Phase 2: Building Map Service

Creating utils/map_service.py with:
- UMAP/t-SNE dimensionality reduction (scikit-learn t-SNE, no extra umap-learn dep)
- K-means clustering with LLM cluster labeling
- Fallback to random layout if no embeddings exist

Also adding scikit-learn to requirements.txt

## Phase 3: Complete

### Files Created/Modified

**Backend:**
- `utils/map_service.py` (NEW) — t-SNE 2D reduction, k-means clustering, LLM cluster labels
- `api/worlds.py` — added GET /api/worlds/map (before /{world_id} to avoid route shadowing)
- `requirements.txt` — added scikit-learn>=1.4.0, numpy>=1.26.0
- `scripts/backfill_embeddings.py` (NEW) — seeds embeddings for all worlds

**Frontend:**
- `app/map/page.tsx` (NEW) — /map route, The Archaeology page
- `components/world/WorldMapCanvas.tsx` (NEW) — D3 constellation visualization
- `components/layout/Header.tsx` — added MAP nav link
- `package.json` + `bun.lock` — added d3@7.9.0

### Key Decisions
- pgvector already existed (migration 0003) — no new migration needed
- t-SNE via scikit-learn (no umap-learn dep)
- Route order fixed: /map before /{world_id}

### Verification
- bun run typecheck — PASSED (0 errors)
- Python syntax check — PASSED
- Route ordering — CORRECT

## Harness Review — Post-Commit Verification (2026-02-17)

Changes reviewed from harness: `platform/backend/api/worlds.py`, `platform/backend/utils/map_service.py`,
`platform/backend/requirements.txt`, `platform/bun.lock`, `platform/package.json`,
`platform/components/layout/Header.tsx`, `platform/e2e/worlds.spec.ts`

Notable fixes applied:
- `asyncio.get_event_loop()` → `asyncio.get_running_loop()` in `map_service.py` (deprecation fix for Python 3.10+)
- E2E tests added for `/map` page (heading visibility, nav link, no-crash states)

### Test Results

```
pytest tests/ --ignore=tests/simulation --ignore=tests/test_media.py --ignore=tests/test_reviews.py -x --tb=short -q
77 passed, 213 skipped, 25 warnings in 11.38s
```

### TypeScript

```
npx tsc --noEmit
0 errors
```
