"""Common nested models reused across multiple schema files."""

from pydantic import BaseModel


class AgentSummary(BaseModel):
    """Lightweight agent reference embedded in other responses."""

    id: str
    username: str
    display_name: str | None = None
    model_id: str | None = None


class WorldSummary(BaseModel):
    """Lightweight world reference embedded in other responses."""

    id: str
    name: str
    premise: str | None = None
    year: int | None = None


class DwellerSummary(BaseModel):
    """Lightweight dweller reference embedded in other responses."""

    id: str
    name: str
    world_id: str
    region: str | None = None
