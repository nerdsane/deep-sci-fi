"""Deterministic replacements for secrets/random/uuid.

Production: real entropy. Simulation: seeded RNG from simulation.py.
"""

import base64
import random as _random_module
import secrets
import uuid

from utils.simulation import get_rng, is_simulation


def generate_token(nbytes: int = 32) -> str:
    rng = get_rng()
    if is_simulation() and rng is not None:
        return base64.urlsafe_b64encode(rng.randbytes(nbytes)).rstrip(b"=").decode()
    return secrets.token_urlsafe(nbytes)


def randint(a: int, b: int) -> int:
    rng = get_rng()
    if is_simulation() and rng is not None:
        return rng.randint(a, b)
    return _random_module.randint(a, b)


def deterministic_uuid4() -> uuid.UUID:
    rng = get_rng()
    if is_simulation() and rng is not None:
        return uuid.UUID(int=rng.getrandbits(128), version=4)
    return uuid.uuid4()
