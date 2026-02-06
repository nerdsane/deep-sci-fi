"""Unified simulation layer (FoundationDB pattern).

Production: all calls delegate to real implementations.
Simulation: clock is manual, RNG is seeded, network is intercepted,
tokens are deterministic.

Usage in production code:
    from utils.sim import sim
    now = sim.clock.now()
    if sim.buggify(0.3): await sim.delay()
    token = sim.token(32)
"""

from utils.clock import now, set_clock, reset_clock, get_clock, SimulatedClock
from utils.deterministic import deterministic_uuid4, generate_token, randint
from utils.simulation import (
    buggify,
    buggify_delay,
    get_rng,
    init_simulation,
    is_simulation,
    reset_simulation,
)


class _NetworkRecorder:
    """Intercepts outbound HTTP in simulation. Records calls for invariant checking."""

    __slots__ = ("calls",)

    def __init__(self):
        self.calls: list[dict] = []

    def record(self, method: str, url: str, payload: dict | None = None):
        self.calls.append({"method": method, "url": url, "payload": payload})

    def reset(self):
        self.calls.clear()


class Sim:
    """Unified simulation context. One import, all layers."""

    # Clock
    now = staticmethod(now)
    set_clock = staticmethod(set_clock)
    reset_clock = staticmethod(reset_clock)
    get_clock = staticmethod(get_clock)
    SimulatedClock = SimulatedClock

    # RNG / BUGGIFY
    buggify = staticmethod(buggify)
    delay = staticmethod(buggify_delay)
    init = staticmethod(init_simulation)
    reset_rng = staticmethod(reset_simulation)
    is_active = staticmethod(is_simulation)
    get_rng = staticmethod(get_rng)

    # Deterministic tokens
    token = staticmethod(generate_token)
    randint = staticmethod(randint)
    uuid4 = staticmethod(deterministic_uuid4)

    # Network
    network = _NetworkRecorder()

    @classmethod
    def reset_all(cls):
        """Full teardown — call in test cleanup."""
        cls.reset_clock()
        cls.reset_rng()
        cls.network.reset()


sim = Sim()
