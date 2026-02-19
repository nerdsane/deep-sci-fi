# PROP-015 Architecture: World Semantic Map — "The Archaeology"

## Vision

A beautiful visual map of all DSF worlds, positioned by thematic similarity. Worlds that explore related ideas cluster together. The map reveals the intellectual landscape of the platform — which corners of speculative thought are dense, which are unexplored.

Not a genealogy tree. A constellation map of ideas.

## Implementation

### Phase 1: Embeddings

#### 1. Generate world embeddings
- For each world: concatenate name + premise + era + region descriptions + key themes
- Generate embedding via XAI or OpenAI embeddings API
- Store as `World.embedding` (vector column, pgvector)
- Re-generate on world update/graduation

#### 2. Migration + pgvector
- Enable pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector`
- Add `embedding vector(1536)` column to worlds table
- (1536 for OpenAI ada-002, or adjust for XAI embedding dimensions)

#### 3. Backfill
- Generate embeddings for all 12 existing worlds
- Cost: negligible (embeddings are ~$0.0001/world)

### Phase 2: Similarity API

#### 4. Endpoint: `GET /api/worlds/map`
Returns all worlds with 2D coordinates derived from embeddings:
```json
{
  "worlds": [
    {
      "id": "uuid",
      "name": "Kept",
      "era": "2043",
      "premise_short": "Grieftech...",
      "dweller_count": 3,
      "status": "active",
      "x": 0.34,
      "y": -0.71,
      "cover_url": "...",
      "cluster": "identity-memory"
    }
  ]
}
```

#### 5. Dimensionality reduction
- Use UMAP or t-SNE to project 1536-dim embeddings → 2D coordinates
- Run server-side on request (12 worlds is instant)
- Or pre-compute and cache (refresh on new world)

#### 6. Cluster labeling
- K-means or DBSCAN on embeddings to find natural clusters
- Use LLM to generate a human-readable cluster label from the member worlds
- "identity & memory", "labor & autonomy", "ecology & collapse"

### Phase 3: Frontend — The Map

#### 7. New page: `/map` or `/archaeology`
Full-page interactive visualization:
- Each world is a node, positioned by semantic coordinates
- Node size = dweller count (activity level)
- Node color = cluster membership
- Subtle connecting lines between nearest neighbors (opacity = similarity)
- Cluster labels as soft background text
- Click node → world detail page
- Hover → world name, era, premise snippet

#### 8. Visual design
- Dark background (space/constellation feel)
- Worlds as glowing points or small circles with world cover art as texture
- Clusters as soft nebula-like regions
- Smooth zoom/pan
- If world has cover_url (from PROP-010): use as node thumbnail

#### 9. Responsive
- Desktop: full interactive D3 canvas
- Mobile: simplified static layout or scrollable list grouped by cluster

### Phase 4: Living Map (Future)

#### 10. Auto-update
- When new world is created, generate embedding, recompute 2D projection
- When world gets more dwellers/stories, node grows
- Dead worlds fade/dim

## Files Changed
- `platform/backend/models/world.py` — add embedding column
- `platform/backend/migrations/` — pgvector + embedding column
- `platform/backend/api/worlds.py` — `/map` endpoint
- `platform/backend/services/embeddings.py` — NEW: generate + reduce + cluster
- `platform/frontend/src/pages/WorldMap.tsx` — NEW page
- `platform/frontend/src/components/WorldMapCanvas/` — NEW D3 component
- `platform/frontend/src/router.tsx` — add route
- `scripts/backfill_embeddings.py` — one-time backfill

## Dependencies
- pgvector (Postgres extension — check Railway/Supabase support)
- Embedding API (OpenAI ada-002 or XAI equivalent)
- D3.js or deck.gl for visualization
- scikit-learn for UMAP/t-SNE (server-side, can use lightweight impl)

## Risk Assessment
- **Database**: pgvector extension needed — must verify Railway Postgres supports it
- **API**: New endpoint only, nothing existing changes
- **Frontend**: New page, no existing pages modified
- **Cost**: Embedding generation is negligible (~$0.001 total for 12 worlds)
- **Rollback**: Drop extension + column + route, zero impact

## Open Questions
- Does Railway's Postgres support pgvector? If not, store embeddings as JSON array and compute similarity in Python.
- XAI embeddings vs OpenAI? Use whichever is already available in the stack.

## Estimated Effort: 6-8 hours CC time
