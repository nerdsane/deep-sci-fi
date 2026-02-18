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
    min_weight: int = Query(1, ge=1, description="Minimum edge weight (co-occurrence count)"),
    db: AsyncSession = Depends(get_db),
):
    """Return the dweller relationship graph for D3 visualization.

    Nodes are dwellers. Edges represent co-occurrence in stories —
    how often two dwellers appear in the same narrative.

    Query params:
    - `world_id`: restrict to one world (optional)
    - `min_weight`: only include edges with at least this many shared stories (default 1)

    Response shape:
    ```json
    {
      "nodes": [{"id": "uuid", "name": "str", "portrait_url": "str|null", "world": "str", "world_id": "uuid"}],
      "edges": [{"source": "uuid", "target": "uuid", "weight": 3, "stories": ["uuid"]}],
      "clusters": [{"id": 0, "label": "str", "dweller_ids": ["uuid"], "world_id": "uuid"}]
    }
    ```
    """
    return await get_dweller_graph(db, world_id=world_id, min_weight=min_weight)
