"""Test data generators for DST simulation.

Counter-based uniqueness ensures deterministic, non-colliding names.

STRATEGY_SCHEMA_MAP maps generator function names to (module_path, model_name)
pairs. The conftest validates that each generator produces data accepted by
the corresponding Pydantic model, catching schema drift.
"""

# Reuse constants from existing tests
SAMPLE_CAUSAL_CHAIN = [
    {
        "year": 2028,
        "event": "First commercial fusion reactor achieves net energy gain",
        "reasoning": "ITER demonstrates Q>10, private companies race to commercialize",
    },
    {
        "year": 2032,
        "event": "Fusion power becomes cost-competitive with natural gas",
        "reasoning": "Learning curve drives costs down, carbon pricing makes fossil fuels expensive",
    },
    {
        "year": 2040,
        "event": "Global energy abundance enables large-scale desalination",
        "reasoning": "Cheap electricity makes previously uneconomical water production viable",
    },
]

VALID_RESEARCH = (
    "I researched the scientific basis by reviewing ITER progress reports, fusion startup "
    "funding trends, and historical energy cost curves. The causal chain aligns with "
    "mainstream fusion research timelines and economic projections from IEA reports."
)

_counter = 0


def _next_id() -> int:
    global _counter
    _counter += 1
    return _counter


def reset_counter() -> None:
    global _counter
    _counter = 0


def proposal_data(counter: int | None = None) -> dict:
    n = counter if counter is not None else _next_id()
    return {
        "name": f"DST World {n}",
        "premise": f"In 2089, fusion energy transformed civilization {n}. "
                   "Abundant clean energy reshaped geopolitics, economics, and daily life.",
        "year_setting": 2089,
        "causal_chain": SAMPLE_CAUSAL_CHAIN,
        "scientific_basis": (
            f"Based on ITER Q>10 results and DOE fusion milestone projections {n}. "
            "Commercial viability follows historical learning curves for energy technologies."
        ),
    }


def validation_data(verdict: str = "approve") -> dict:
    base = {
        "verdict": verdict,
        "research_conducted": VALID_RESEARCH,
        "critique": "Thorough analysis with sufficient length for validation requirements.",
        "scientific_issues": [],
        "suggested_fixes": [],
    }
    if verdict == "approve":
        base["weaknesses"] = ["Timeline optimism in intermediate steps"]
    return base


def region_data(counter: int | None = None) -> dict:
    n = counter if counter is not None else _next_id()
    return {
        "name": f"Region {n}",
        "location": f"Location {n}",
        "population_origins": [f"Origin A{n}", f"Origin B{n}"],
        "cultural_blend": f"Cultural blend of diverse origins forming region {n} identity over generations",
        "naming_conventions": (
            f"Names follow test conventions {n}: First names are simple, "
            "family names reflect test heritage. Examples: Test Person, Sample Name."
        ),
        "language": "Test English",
    }


def dweller_data(region_name: str, counter: int | None = None) -> dict:
    n = counter if counter is not None else _next_id()
    return {
        "name": f"Dweller {n}",
        "origin_region": region_name,
        "generation": "First-generation",
        "name_context": (
            f"Dweller {n} is a test name following region conventions; "
            "the surname references the local geography of early settlements."
        ),
        "cultural_identity": f"Test cultural identity {n}",
        "role": f"Test role {n}",
        "age": 30,
        "personality": (
            f"A test personality {n} with sufficient detail to meet the minimum "
            "character requirements for dweller creation validation."
        ),
        "background": (
            f"Test background story {n} for the dweller character with "
            "enough detail to meet the minimum validation requirements."
        ),
    }


def feedback_data(counter: int | None = None) -> dict:
    n = counter if counter is not None else _next_id()
    return {
        "title": f"Test Feedback {n}",
        "description": (
            f"This is test feedback item {n} with sufficient description "
            "to meet minimum validation requirements."
        ),
        "category": "api_bug",
        "priority": "medium",
        "endpoint": "/api/test",
    }


def action_data(importance: float = 0.3) -> dict:
    return {
        "action_type": "speak",
        "content": "Hello, this is a test action with sufficient content.",
        "importance": importance,
    }


def high_importance_action_data() -> dict:
    return {
        "action_type": "decide",
        "content": "This is a high-importance decision that could reshape the world order.",
        "importance": 0.9,
    }


def story_data(world_id: str, counter: int | None = None) -> dict:
    n = counter if counter is not None else _next_id()
    return {
        "world_id": world_id,
        "title": f"Story of the Future {n}",
        "content": (
            f"In the year 2089, the world had changed beyond recognition {n}. "
            "The fusion revolution had reshaped every aspect of human civilization. "
            "Energy was abundant, water was plentiful, and the old scarcities that "
            "had driven so much conflict were fading memories. But new challenges "
            "emerged — challenges that tested the very fabric of identity and purpose."
        ),
        "perspective": "third_person_omniscient",
    }


def review_data(recommend_acclaim: bool = True) -> dict:
    return {
        "recommend_acclaim": recommend_acclaim,
        "improvements": ["Consider adding more sensory detail to grounding scenes"],
        "canon_notes": "Story aligns well with established world canon and causal chain events.",
        "event_notes": "Events referenced match the world timeline and are internally consistent.",
        "style_notes": "Writing quality is solid with clear narrative arc and consistent perspective.",
    }


def review_response_data() -> dict:
    return {
        "response": "Thank you for the thoughtful review. I have considered your feedback carefully.",
    }


def story_reaction_data() -> dict:
    return {
        "reaction_type": "fire",
    }


def comment_data(target_type: str = "world", target_id: str = "") -> dict:
    n = _next_id()
    return {
        "target_type": target_type,
        "target_id": target_id,
        "content": f"Test comment {n} with enough content to be meaningful.",
    }


def social_reaction_data(target_type: str = "world", target_id: str = "") -> dict:
    return {
        "target_type": target_type,
        "target_id": target_id,
        "reaction_type": "fire",
    }


def follow_data(target_type: str = "world", target_id: str = "") -> dict:
    return {
        "target_type": target_type,
        "target_id": target_id,
    }


def aspect_data(world_id: str = "", aspect_type: str = "technology", counter: int | None = None) -> dict:
    n = counter if counter is not None else _next_id()
    return {
        "aspect_type": aspect_type,
        "title": f"Aspect {n}: Advanced Fusion Grid",
        "premise": (
            f"The global fusion grid {n} connects decentralized reactors "
            "through quantum-encrypted superconducting transmission lines."
        ),
        "content": {
            "description": f"Technical details of the fusion grid {n}",
            "impact": "Enables instant energy transfer across continents",
        },
        "canon_justification": (
            f"This aspect {n} extends the world's fusion premise by detailing "
            "the distribution infrastructure. The causal chain establishes "
            "commercial fusion by 2032; grid infrastructure naturally follows."
        ),
    }


def aspect_validation_data(verdict: str = "approve", world_name: str = "Test World") -> dict:
    base = {
        "verdict": verdict,
        "critique": f"This aspect is well-grounded in the {world_name} canon and adds meaningful depth.",
        "canon_conflicts": [],
        "suggested_fixes": [],
    }
    if verdict == "approve":
        base["updated_canon_summary"] = (
            f"The world of {world_name} now includes advanced fusion grid technology. "
            "This infrastructure enables instant energy transfer across continents, "
            "further solidifying the post-scarcity energy economy established in the premise."
        )
    return base


def suggestion_data(field: str = "premise") -> dict:
    n = _next_id()
    return {
        "field": field,
        "suggested_value": f"Improved premise {n} with more specific grounding in verified research.",
        "rationale": (
            f"The current {field} lacks specificity {n}. This revision grounds the claim "
            "in verifiable research and provides clearer causal reasoning."
        ),
    }


def suggestion_response_data(accept: bool = True) -> dict:
    return {
        "reason": "The suggested revision improves clarity and grounding. Accepted with gratitude."
        if accept
        else "The current formulation is intentional and serves the narrative better.",
    }


def event_data(world_id: str = "", year: int = 2035, counter: int | None = None) -> dict:
    n = counter if counter is not None else _next_id()
    return {
        "title": f"The Great Convergence {n}",
        "description": (
            f"Event {n}: A pivotal moment when fusion grid operators across "
            "three continents synchronized their output for the first time, "
            "demonstrating the feasibility of global energy coordination."
        ),
        "year_in_world": year,
        "canon_justification": (
            f"This event {n} follows naturally from the commercial fusion "
            "milestone in 2032 and the subsequent infrastructure buildout. "
            "Continental grid synchronization is the logical next step."
        ),
    }


def event_approve_data(world_name: str = "Test World") -> dict:
    return {
        "canon_update": (
            f"The world of {world_name} experienced a pivotal convergence event. "
            "Fusion grid operators across continents synchronized their output, "
            "proving global energy coordination is achievable and reshaping geopolitics."
        ),
    }


def event_reject_data() -> dict:
    return {
        "reason": "The event contradicts established timeline and lacks sufficient grounding.",
    }


def confirm_importance_data() -> dict:
    return {
        "rationale": "This action has significant world-changing implications and deserves escalation.",
    }


def escalate_data(year: int = 2035) -> dict:
    n = _next_id()
    return {
        "title": f"Escalated Event {n}",
        "description": (
            f"Escalated event {n}: A dweller action of sufficient importance "
            "to reshape the world's causal chain. The consequences ripple "
            "through multiple regions and affect countless inhabitants."
        ),
        "year_in_world": year,
    }


def dweller_proposal_data(region_name: str, counter: int | None = None) -> dict:
    n = counter if counter is not None else _next_id()
    return {
        "name": f"Proposed Dweller {n}",
        "origin_region": region_name,
        "generation": "Second-gen",
        "name_context": (
            f"Proposed Dweller {n} follows the region naming conventions; "
            "the name reflects second-generation cultural fusion patterns."
        ),
        "cultural_identity": (
            f"A second-generation inhabitant {n} blending founding traditions "
            "with emergent regional culture."
        ),
        "role": f"Community liaison {n}",
        "age": 25,
        "personality": (
            f"Proposed Dweller {n} is thoughtful and diplomatic, bridging "
            "generational divides with empathy and practical wisdom."
        ),
        "background": (
            f"Born into the second wave of settlement {n}, grew up mediating "
            "between founding elders and new arrivals."
        ),
    }


def validation_data_strengthen() -> dict:
    return {
        "verdict": "strengthen",
        "research_conducted": VALID_RESEARCH,
        "critique": "The proposal has potential but needs work on the causal chain specificity and scientific grounding.",
        "scientific_issues": ["Causal chain step 2 lacks specific actors with clear incentives"],
        "suggested_fixes": ["Add intermediate steps between 2032 and 2040 with named organizations"],
    }


def proposal_revise_data() -> dict:
    return {
        "scientific_basis": (
            "Revised basis: Based on ITER Q>10 results (2025), Helion Energy's milestone, "
            "and DOE fusion milestone projections. Commercial viability follows historical "
            "learning curves for energy technologies, specifically paralleling solar PV adoption rates."
        ),
    }


def aspect_validation_data_strengthen() -> dict:
    return {
        "verdict": "strengthen",
        "critique": "The aspect has potential but the canon justification needs to reference specific causal chain events.",
        "canon_conflicts": [],
        "suggested_fixes": ["Strengthen the canon justification with specific timeline references"],
    }


def aspect_revise_data() -> dict:
    return {
        "canon_justification": (
            "Revised justification: This aspect extends the world's fusion premise by detailing "
            "the distribution infrastructure. The causal chain establishes commercial fusion by 2032 "
            "and cost-competitiveness by 2040; grid infrastructure naturally follows as demand scales."
        ),
    }


def dweller_proposal_validation_data_strengthen() -> dict:
    return {
        "verdict": "strengthen",
        "critique": "The character concept is interesting but the name context needs deeper connection to the region's naming conventions.",
        "cultural_issues": ["Name context doesn't sufficiently explain naming convention alignment"],
        "suggested_fixes": ["Elaborate on how the name reflects second-generation cultural fusion"],
    }


def dweller_proposal_revise_data() -> dict:
    return {
        "name_context": (
            "Revised context: The name reflects second-generation cultural fusion patterns "
            "where founding families blended heritage naming with regional adaptations, "
            "creating a distinctive naming tradition unique to the settlement."
        ),
    }


def dweller_proposal_validation_data(verdict: str = "approve") -> dict:
    base = {
        "verdict": verdict,
        "critique": (
            "This dweller proposal demonstrates strong cultural grounding "
            "and a well-developed character that fits the world's context."
        ),
    }
    if verdict != "approve":
        base["suggested_fixes"] = ["Consider deepening the cultural identity section"]
    return base


# ---------------------------------------------------------------------------
# Schema registry: maps generator -> (module_path, Pydantic model name)
# Used by conftest.py to detect schema drift at test startup.
# ---------------------------------------------------------------------------

STRATEGY_SCHEMA_MAP = {
    "proposal_data": ("api.proposals", "ProposalCreateRequest"),
    "validation_data": ("api.proposals", "ValidationCreateRequest"),
    "region_data": ("api.dwellers", "RegionCreateRequest"),
    "dweller_data": ("api.dwellers", "DwellerCreateRequest"),
    "feedback_data": ("api.feedback", "FeedbackCreateRequest"),
    # action_data and high_importance_action_data are excluded:
    # they produce partial payloads used by _act_with_context_sync(),
    # which adds context_token from the /act/context endpoint.
    "story_data": ("api.stories", "StoryCreateRequest"),
    "review_data": ("api.stories", "StoryReviewRequest"),
    "review_response_data": ("api.stories", "ReviewResponseRequest"),
    "story_reaction_data": ("api.stories", "ReactionRequest"),
    "aspect_data": ("api.aspects", "AspectCreateRequest"),
    "aspect_validation_data": ("api.aspects", "AspectValidationRequest"),
    "suggestion_data": ("api.suggestions", "SuggestRevisionRequest"),
    "suggestion_response_data": ("api.suggestions", "RespondToSuggestionRequest"),
    "event_data": ("api.events", "EventCreateRequest"),
    "event_approve_data": ("api.events", "EventApproveRequest"),
    "event_reject_data": ("api.events", "EventRejectRequest"),
    "confirm_importance_data": ("api.actions", "ConfirmImportanceRequest"),
    "escalate_data": ("api.actions", "EscalateRequest"),
    "dweller_proposal_data": ("api.dweller_proposals", "DwellerProposalCreateRequest"),
    "validation_data_strengthen": ("api.proposals", "ValidationCreateRequest"),
    "proposal_revise_data": ("api.proposals", "ProposalReviseRequest"),
    "aspect_validation_data_strengthen": ("api.aspects", "AspectValidationRequest"),
    "aspect_revise_data": ("api.aspects", "AspectReviseRequest"),
    "dweller_proposal_validation_data_strengthen": ("api.dweller_proposals", "DwellerValidationCreateRequest"),
    "dweller_proposal_revise_data": ("api.dweller_proposals", "DwellerProposalReviseRequest"),
    "dweller_proposal_validation_data": ("api.dweller_proposals", "DwellerValidationCreateRequest"),
    "comment_data": ("api.social", "CommentRequest"),
    "social_reaction_data": ("api.social", "ReactionRequest"),
    "follow_data": ("api.social", "FollowRequest"),
}
