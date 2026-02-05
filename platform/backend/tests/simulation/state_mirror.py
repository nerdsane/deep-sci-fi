"""State tracking dataclasses for DST simulation.

Mirrors expected state from API responses. Invariants query API/DB directly
for truth — this is just bookkeeping to know what rules are available.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class AgentState:
    agent_id: str
    api_key: str
    username: str
    last_heartbeat: datetime | None = None


@dataclass
class ProposalState:
    proposal_id: str
    creator_id: str
    status: str  # from API response
    validators: dict[str, str] = field(default_factory=dict)  # agent_id -> verdict


@dataclass
class WorldState:
    world_id: str
    creator_id: str
    source_proposal_id: str
    regions: list[str] = field(default_factory=list)


@dataclass
class DwellerState:
    dweller_id: str
    world_id: str
    origin_region: str


@dataclass
class FeedbackState:
    feedback_id: str
    creator_id: str


@dataclass
class SimulationState:
    agents: dict[str, AgentState] = field(default_factory=dict)
    proposals: dict[str, ProposalState] = field(default_factory=dict)
    worlds: dict[str, WorldState] = field(default_factory=dict)
    dwellers: dict[str, DwellerState] = field(default_factory=dict)
    feedback: dict[str, FeedbackState] = field(default_factory=dict)
    error_log: list[dict] = field(default_factory=list)  # 500 responses
