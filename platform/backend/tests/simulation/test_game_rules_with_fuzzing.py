"""Pydantic-driven property-based fuzz testing layer on top of core DST.

Inherits all rules + invariants from DeepSciFiGameRules. Adds ~10 fuzz rules
that draw data from Pydantic request models via Hypothesis, exercising:
- Boundary values (min/max length strings, ge/le integers)
- All enum variants (not just the 1 value deterministic generators pick)
- Optional field diversity (sometimes None, sometimes populated)
- Nested model variation (diverse causal chains, feedback items, etc.)

The key signal: `assert resp.status_code < 500`. Validation errors (4xx) are
expected and fine — they prove the API rejects bad input gracefully. Server
errors (5xx) are bugs.

State tracking on success keeps invariants working: fuzzed entities that pass
validation get tracked just like deterministic ones.
"""

from hypothesis import settings, HealthCheck

from tests.simulation.test_game_rules import DeepSciFiGameRules
from tests.simulation.rules.fuzz import FuzzRulesMixin
from tests.simulation.rules.fuzz_chains import CrossDomainFuzzMixin, FuzzChainRulesMixin


class FuzzedGameRules(FuzzChainRulesMixin, CrossDomainFuzzMixin, FuzzRulesMixin, DeepSciFiGameRules):
    """Extended state machine with Pydantic-driven fuzz rules + cross-domain chains.

    Inherits ALL existing rules + invariants. Fuzz rules interleave with
    deterministic rules, catching bugs from diverse data that fixed generators
    never produce (boundary years, max-length strings, all enum variants).
    Cross-domain rules stress entity interactions across domain boundaries.
    """


# Run the state machine
TestGameRulesWithFuzzing = FuzzedGameRules.TestCase
TestGameRulesWithFuzzing.settings = settings(
    max_examples=30,
    stateful_step_count=20,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
