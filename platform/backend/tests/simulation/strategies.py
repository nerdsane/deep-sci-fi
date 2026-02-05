"""Test data generators for DST simulation.

Counter-based uniqueness ensures deterministic, non-colliding names.
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
        "background": f"Test background story {n} for the dweller character",
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


def action_data() -> dict:
    return {
        "action_type": "speak",
        "content": "Hello, this is a test action with sufficient content.",
        "importance": 0.3,
    }
