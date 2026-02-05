"""BUGGIFY: Deterministic fault injection (FoundationDB pattern).

Production: all calls are no-ops. Simulation: seeded RNG controls chaos.
Zero overhead in production — buggify() returns False without touching RNG.
"""

import asyncio
import os
import random as _random_module

_SIMULATION_MODE: bool = os.getenv("DST_SIMULATION", "").lower() in ("1", "true")
_rng: _random_module.Random | None = None
_seed: int | None = None


def init_simulation(seed: int) -> None:
    global _SIMULATION_MODE, _rng, _seed
    _SIMULATION_MODE = True
    _seed = seed
    _rng = _random_module.Random(seed)


def is_simulation() -> bool:
    return _SIMULATION_MODE


def buggify(probability: float = 0.5) -> bool:
    if not _SIMULATION_MODE or _rng is None:
        return False
    return _rng.random() < probability


async def buggify_delay(min_s: float = 0.001, max_s: float = 0.050) -> None:
    if not _SIMULATION_MODE or _rng is None:
        return
    await asyncio.sleep(_rng.uniform(min_s, max_s))


def reset_simulation() -> None:
    global _SIMULATION_MODE, _rng, _seed
    _SIMULATION_MODE = False
    _rng = None
    _seed = None
