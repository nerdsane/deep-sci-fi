# PROP-015 Architecture: World Genealogy Visualization — "The Archaeology"

## Approach: Manual Metadata + D3 Force Graph

Start with explicit world relationships (manual/proposal-derived), render with D3.

## Implementation

### Phase 1: Data Model

#### 1. New model: `WorldRelation`
```python
class WorldRelation(Base):
    __tablename__ = "world_relations"
    id = Column(UUID, primary_key=True)
    source_world_id = Column(UUID, ForeignKey("worlds.id"))
    target_world_id = Column(UUID, ForeignKey("worlds.id"))
    relation_type = Column(String)  # "inspired_by", "thematic_sibling", "evolution_of"
    description = Column(Text, nullable=True)  # "Kept explores grieftech themes seeded in Felt"
    created_at = Column(DateTime, default=utc_now)
```

#### 2. Migration
Add `world_relations` table.

#### 3. API endpoint: `GET /api/worlds/genealogy`
Returns nodes (worlds with metadata) + edges (relations) in D3-friendly format:
```json
{
  "nodes": [{"id": "uuid", "name": "Kept", "era": "2043", "dweller_count": 3, "status": "active"}],
  "edges": [{"source": "felt-uuid", "target": "kept-uuid", "type": "inspired_by", "label": "grieftech themes"}]
}
```

### Phase 2: Frontend Visualization

#### 4. New page: `/genealogy` or `/archaeology`
Full-page D3 force-directed graph:
- Nodes sized by dweller count
- Color-coded by world status (active/dead)
- Edges labeled with relation type
- Click node → navigate to world page
- Responsive: works on mobile (simpler layout)

#### 5. D3 component
```tsx
// WorldGenealogy.tsx
// Use d3-force for layout, SVG for rendering
// Nodes: circles with world name labels
// Edges: curved lines with hover tooltips
```

#### 6. Seed initial relations
Based on existing world descriptions and proposal lineages:
- Recalled → Kept (memory themes)
- Felt → Kept (posthumous continuation)
- Recalled → Felt (identity/memory)
- etc.

Admin endpoint or migration seed to populate.

### Phase 3: Auto-inference (Future)

#### 7. Proposal text analysis (later)
When a world proposal references another world, auto-suggest a relation. Not in this PR.

## Files Changed
- `platform/backend/models/world_relation.py` — NEW model
- `platform/backend/migrations/` — new migration
- `platform/backend/api/worlds.py` — genealogy endpoint
- `platform/frontend/src/pages/Genealogy.tsx` — NEW page
- `platform/frontend/src/components/WorldGraph/` — NEW D3 component
- `platform/frontend/src/router.tsx` — add route
- `scripts/seed_world_relations.py` — initial data

## Dependencies
- D3.js (add to frontend deps)
- Existing world data

## Risk Assessment
- **Database**: New table, no existing tables modified
- **API**: New endpoint only, nothing existing changes
- **Frontend**: New page, no existing pages modified
- **Rollback**: Drop table + remove route, zero impact on existing functionality

## Estimated Effort: 4-6 hours CC time
