# PROP-009: Relationship Graphs — Architecture

## Overview
Visualize dweller-to-dweller relationships based on co-occurrence in stories and actions.

## Data Model
No new tables. Relationships computed from existing data:
- Stories: `perspective_dweller_id` + mentions in content
- Actions: `dweller_id` + references to other dwellers
- Same-world proximity (dwellers in same world have baseline connection)

## Service: `platform/backend/utils/relationship_service.py`

```python
async def get_dweller_graph(world_id: Optional[UUID] = None) -> dict:
    """
    Returns nodes (dwellers) and edges (relationships) for D3 visualization.
    
    Algorithm:
    1. Query all stories, group by perspective_dweller
    2. For each story, find other dwellers mentioned (by name match in content)
    3. For each action, find dweller references
    4. Build edge weights: co-occurrence count = edge strength
    5. Return {nodes: [{id, name, portrait_url, world_name}], edges: [{source, target, weight, stories}]}
    """
```

## API: `GET /api/dwellers/graph`

Query params:
- `world_id` (optional) — filter to one world
- `min_weight` (optional, default 1) — minimum co-occurrence to show edge

Response:
```json
{
  "nodes": [{"id": "uuid", "name": "string", "portrait_url": "string", "world": "string"}],
  "edges": [{"source": "uuid", "target": "uuid", "weight": 3, "stories": ["uuid"]}],
  "clusters": [{"id": 0, "label": "string", "dweller_ids": ["uuid"]}]
}
```

## Frontend: `/web` page

- D3 force-directed graph (reuse patterns from WorldMapCanvas.tsx)
- Nodes = dweller portraits (circular images, fallback to initials)
- Edges = lines with thickness proportional to weight
- Color by world
- Click node → navigate to dweller detail
- Click edge → show shared stories
- Filter dropdown by world
- Mobile: simplified layout, tap interactions

## Files to create/modify
1. NEW: `platform/backend/utils/relationship_service.py`
2. NEW: `platform/backend/api/dweller_graph.py` (or add to existing dwellers.py)
3. MODIFY: `platform/backend/api/__init__.py` — mount new router
4. NEW: `platform/app/web/page.tsx`
5. NEW: `platform/components/graph/DwellerGraphCanvas.tsx`
6. MODIFY: `platform/components/Header.tsx` — add WEB nav link
7. MODIFY: `platform/components/MobileNav.tsx` — add WEB nav link
8. NEW: `platform/lib/api.ts` — add getDwellerGraph()

## Risk
High — new endpoint, new service, new page. But no migrations. All data computed from existing tables.

## Branch
`feat/dweller-relationship-graph`
