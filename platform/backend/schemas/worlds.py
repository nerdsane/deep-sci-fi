"""Pydantic response schemas for worlds API endpoints."""

from pydantic import BaseModel, Field

from schemas.base import PaginatedResponse


class WorldItem(BaseModel):
    """A world in list/catalog views."""

    id: str
    name: str
    premise: str | None = None
    canon_summary: str | None = None
    year_setting: int | None = None
    causal_chain: list[dict] | None = None
    scientific_basis: str | None = None
    regions: list | None = None
    proposal_id: str | None = None
    cover_image_url: str | None = None
    created_at: str
    dweller_count: int = 0
    follower_count: int = 0
    comment_count: int = 0
    reaction_counts: dict = Field(default_factory=dict)


class WorldDetail(WorldItem):
    """Full world details (includes updated_at)."""

    updated_at: str


# -- Endpoint response models --


class WorldSearchResult(BaseModel):
    """Single result from semantic search."""
    # Shape depends on find_similar_worlds output; keep it flexible
    id: str
    name: str | None = None
    premise: str | None = None
    similarity: float | None = None

    model_config = {"extra": "allow"}


class WorldSearchResponse(BaseModel):
    """GET /worlds/search"""

    query: str
    results: list[dict]
    count: int


class WorldMapNode(BaseModel):
    """A single node in the world map."""

    id: str
    name: str
    premise: str | None = None
    premise_short: str | None = None
    year_setting: int | None = None
    cover_image_url: str | None = None
    dweller_count: int = 0
    follower_count: int = 0
    x: float | None = None
    y: float | None = None
    cluster: int | None = None
    cluster_label: str | None = None
    cluster_color: str | None = None

    model_config = {"extra": "allow"}


class WorldMapResponse(BaseModel):
    """GET /worlds/map"""

    worlds: list[dict]
    cluster_labels: list[str]
    total: int


class WorldListResponse(PaginatedResponse):
    """GET /worlds"""

    worlds: list[WorldItem]


class WorldDetailResponse(BaseModel):
    """GET /worlds/{world_id}"""

    world: WorldDetail
