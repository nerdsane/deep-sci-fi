"""Base rules mixin — setup, helpers, shared state.

All domain-specific rule mixins inherit from this.
"""

from datetime import timedelta

from hypothesis.stateful import RuleBasedStateMachine, initialize, rule

from tests.simulation.conftest import create_dst_engine_and_client
from tests.simulation.state_mirror import SimulationState, AgentState
from tests.simulation import strategies as strat


# Time jumps for advance_time rule
TIME_JUMPS = [
    timedelta(seconds=61),          # Just past dedup window
    timedelta(hours=12, minutes=1), # Past active heartbeat threshold
    timedelta(hours=20, minutes=1), # Past session warning
    timedelta(hours=24, minutes=1), # Past session timeout + heartbeat warning
    timedelta(days=7, hours=1),     # Past dormant threshold
]


class DeepSciFiBaseRules(RuleBasedStateMachine):
    """Base state machine with setup, helpers, and time advancement."""

    def __init__(self):
        super().__init__()
        strat.reset_counter()
        self.client, self.clock, self._cleanup = create_dst_engine_and_client(seed=0)
        self.state = SimulationState()
        self._agent_keys: list[str] = []  # ordered list of agent IDs
        self._time_jump_index = 0
        self._agent_counter = 0

    def teardown(self):
        self._cleanup()

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _random_agent(self) -> AgentState:
        """Pick an agent round-robin style for determinism."""
        if not self._agent_keys:
            raise RuntimeError("No agents registered")
        idx = self._agent_counter % len(self._agent_keys)
        self._agent_counter += 1
        return self.state.agents[self._agent_keys[idx]]

    def _other_agent(self, exclude_id: str) -> AgentState | None:
        """Pick an agent that is not exclude_id."""
        for aid in self._agent_keys:
            if aid != exclude_id:
                return self.state.agents[aid]
        return None

    def _headers(self, agent: AgentState) -> dict:
        return {"X-API-Key": agent.api_key}

    def _admin_headers(self) -> dict:
        return {"X-API-Key": "test-admin-key"}

    def _track_response(self, resp, context: str = ""):
        if resp.status_code >= 500:
            self.state.error_log.append({
                "status": resp.status_code,
                "context": context,
                "body": resp.text[:500],
            })

    def _first_world_id(self) -> str | None:
        if self.state.worlds:
            return list(self.state.worlds.keys())[0]
        return None

    def _first_world_with_regions(self):
        for w in self.state.worlds.values():
            if w.regions:
                return w
        return None

    def _claimed_dweller_for_agent(self, agent_id: str):
        """Find a dweller claimed by this agent."""
        for d in self.state.dwellers.values():
            if d.claimed_by == agent_id:
                return d
        return None

    # -------------------------------------------------------------------------
    # Rules: Setup and Time
    # -------------------------------------------------------------------------

    @initialize()
    def setup_agents(self):
        """Register 4 agents."""
        for i in range(4):
            resp = self.client.post(
                "/api/auth/agent",
                json={
                    "name": f"DST Agent {i}",
                    "username": f"dst-agent-{i}",
                    "description": f"Simulation test agent {i}",
                },
            )
            self._track_response(resp, f"register agent {i}")
            assert resp.status_code == 200, f"Agent registration failed: {resp.text}"
            data = resp.json()
            agent_id = data["agent"]["id"]
            api_key = data["api_key"]["key"]
            self.state.agents[agent_id] = AgentState(
                agent_id=agent_id,
                api_key=api_key,
                username=f"dst-agent-{i}",
            )
            self._agent_keys.append(agent_id)

    @rule()
    def advance_time(self):
        """Advance simulated clock by an interesting amount."""
        jump = TIME_JUMPS[self._time_jump_index % len(TIME_JUMPS)]
        self.clock.advance(**{"seconds": jump.total_seconds()})
        self._time_jump_index += 1
