"""Dweller relationship graph API.

GET /api/dwellers/graph — returns nodes and edges for D3 visualization.
No auth required (read-only, public data).
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from db import get_db
from utils.relationship_service import get_dweller_graph

router = APIRouter(prefix="/dwellers", tags=["dwellers"])


@router.get("/graph")
async def dweller_graph(
    world_id: Optional[UUID] = Query(None, description="Filter to a single world"),
    min_weight: int = Query(1, ge=1, description="Minimum total interaction count to include edge"),
    db: AsyncSession = Depends(get_db),
):
    """Return the dweller relationship graph for D3 visualization.

    Nodes are dwellers. Edges represent real interaction signals (PROP-022 revision):
    - speak_count_a_to_b / speak_count_b_to_a: directional SPEAK actions
    - story_mention_a_to_b / story_mention_b_to_a: perspective dweller mentions other in story
    - thread_count: back-and-forth reply chains
    - co_occurrence_count: legacy name co-occurrence (kept for backcompat)

    Query params:
    - `world_id`: restrict to one world (optional)
    - `min_weight`: only include edges with at least this total interaction count (default 1)

    Response shape:
    ```json
    {
      "nodes": [{"id": "uuid", "name": "str", "portrait_url": "str|null", "world": "str", "world_id": "uuid"}],
      "edges": [
        {
          "source": "uuid", "target": "uuid", "weight": 12, "combined_score": 0.85,
          "speaks_a_to_b": 8, "speaks_b_to_a": 3,
          "story_mentions_a_to_b": 2, "story_mentions_b_to_a": 0,
          "threads": 4, "last_interaction": "2026-02-18T...", "stories": ["uuid"]
        }
      ],
      "clusters": [{"id": 0, "label": "str", "dweller_ids": ["uuid"], "world_id": "uuid"}]
    }
    ```
    """
    return await get_dweller_graph(db, world_id=world_id, min_weight=min_weight)
