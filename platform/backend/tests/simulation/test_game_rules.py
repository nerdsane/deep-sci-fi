"""Core DST state machine: Can any sequence of valid API calls violate game rules?

45+ rules across 14 domain mixins, 20 safety invariants (every step),
7 liveness invariants (teardown). Uses Hypothesis RuleBasedStateMachine.

Architecture: DeepSciFiBaseRules provides setup + helpers.
Each mixin adds rules for one domain. SafetyInvariantsMixin checks invariants
every step. LivenessInvariantsMixin checks at teardown.

CI profile (--hypothesis-profile=ci) runs 200 examples for thorough exploration.
Default profile runs 50 examples for fast local iteration.
"""

from hypothesis import settings, HealthCheck

# Base rules: setup_agents, advance_time, helpers
from tests.simulation.rules.base import DeepSciFiBaseRules

# Domain rule mixins
from tests.simulation.rules.proposals import ProposalRulesMixin
from tests.simulation.rules.dwellers import DwellerRulesMixin
from tests.simulation.rules.stories import StoryRulesMixin
from tests.simulation.rules.social import SocialRulesMixin
from tests.simulation.rules.feedback import FeedbackRulesMixin
from tests.simulation.rules.aspects import AspectRulesMixin
from tests.simulation.rules.suggestions import SuggestionRulesMixin
from tests.simulation.rules.events import EventRulesMixin
from tests.simulation.rules.actions import ActionRulesMixin
from tests.simulation.rules.dweller_proposals import DwellerProposalRulesMixin
from tests.simulation.rules.notifications import NotificationRulesMixin
from tests.simulation.rules.auth import AuthRulesMixin
from tests.simulation.rules.heartbeat import HeartbeatRulesMixin
from tests.simulation.rules.read_only import ReadOnlyRulesMixin
from tests.simulation.rules.media import MediaRulesMixin

# Invariant mixins
from tests.simulation.invariants.safety import SafetyInvariantsMixin
from tests.simulation.invariants.liveness import LivenessInvariantsMixin


class DeepSciFiGameRules(
    # Invariants (checked every step / at teardown)
    SafetyInvariantsMixin,
    LivenessInvariantsMixin,
    # Domain rules
    ProposalRulesMixin,
    DwellerRulesMixin,
    StoryRulesMixin,
    SocialRulesMixin,
    FeedbackRulesMixin,
    AspectRulesMixin,
    SuggestionRulesMixin,
    EventRulesMixin,
    ActionRulesMixin,
    DwellerProposalRulesMixin,
    NotificationRulesMixin,
    AuthRulesMixin,
    HeartbeatRulesMixin,
    ReadOnlyRulesMixin,
    MediaRulesMixin,
    # Base (must be last — provides RuleBasedStateMachine)
    DeepSciFiBaseRules,
):
    """Full state machine composing all domain rules and invariants.

    Hypothesis interleaves ALL rules, catching cross-domain bugs
    (e.g., story created during proposal validation).
    """

    def teardown(self):
        self.check_liveness_invariants()
        self._cleanup()


# Run the state machine
TestGameRules = DeepSciFiGameRules.TestCase
TestGameRules.settings = settings(
    stateful_step_count=30,
    suppress_health_check=[HealthCheck.too_slow],
    deadline=None,
)
