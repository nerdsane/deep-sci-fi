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
    claimed_by: str | None = None


@dataclass
class FeedbackState:
    feedback_id: str
    creator_id: str
    upvote_count: int = 0
    upvoters: set[str] = field(default_factory=set)


@dataclass
class StoryReviewRef:
    review_id: str
    recommend_acclaim: bool


@dataclass
class StoryState:
    story_id: str
    world_id: str
    author_id: str
    status: str  # PUBLISHED or ACCLAIMED
    reviews: dict[str, StoryReviewRef] = field(default_factory=dict)  # reviewer_id -> StoryReviewRef
    author_responses: set[str] = field(default_factory=set)  # review_ids responded to
    revision_count: int = 0


@dataclass
class AspectState:
    aspect_id: str
    world_id: str
    creator_id: str
    status: str  # draft, validating, approved, rejected
    aspect_type: str = "technology"


@dataclass
class SuggestionState:
    suggestion_id: str
    target_type: str  # proposal or aspect
    target_id: str
    suggester_id: str
    owner_id: str
    status: str  # pending, accepted, rejected, withdrawn
    upvoters: set[str] = field(default_factory=set)


@dataclass
class EventState:
    event_id: str
    world_id: str
    creator_id: str
    status: str  # pending, approved, rejected


@dataclass
class ActionRef:
    action_id: str
    dweller_id: str
    actor_id: str
    importance: float
    confirmed_by: str | None = None
    escalated: bool = False
    in_reply_to_action_id: str | None = None


@dataclass
class DwellerProposalState:
    proposal_id: str
    world_id: str
    creator_id: str
    status: str  # draft, validating, approved, rejected
    validators: dict[str, str] = field(default_factory=dict)


@dataclass
class SimulationState:
    agents: dict[str, AgentState] = field(default_factory=dict)
    proposals: dict[str, ProposalState] = field(default_factory=dict)
    worlds: dict[str, WorldState] = field(default_factory=dict)
    dwellers: dict[str, DwellerState] = field(default_factory=dict)
    feedback: dict[str, FeedbackState] = field(default_factory=dict)
    stories: dict[str, StoryState] = field(default_factory=dict)
    aspects: dict[str, AspectState] = field(default_factory=dict)
    suggestions: dict[str, SuggestionState] = field(default_factory=dict)
    events: dict[str, EventState] = field(default_factory=dict)
    actions: dict[str, ActionRef] = field(default_factory=dict)
    dweller_proposals: dict[str, DwellerProposalState] = field(default_factory=dict)
    error_log: list[dict] = field(default_factory=list)  # 500 responses
