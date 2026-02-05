"""Deterministic clock for simulation testing.

Production: real wall-clock time. Simulation: manually-advanced clock.
Enables deterministic replay of time-dependent logic (session timeouts,
dedup windows, activity thresholds) without mocking datetime globally.
"""

from datetime import datetime, timedelta, timezone
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class _RealClock:
    __slots__ = ()

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class SimulatedClock:
    __slots__ = ("_current_time",)

    def __init__(self, start: datetime | None = None):
        self._current_time = start or datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._current_time

    def advance(self, **kwargs) -> datetime:
        self._current_time += timedelta(**kwargs)
        return self._current_time

    def set(self, time: datetime) -> None:
        self._current_time = time


_clock: Clock = _RealClock()


def now() -> datetime:
    return _clock.now()


def set_clock(clock: Clock) -> None:
    global _clock
    _clock = clock


def reset_clock() -> None:
    global _clock
    _clock = _RealClock()


def get_clock() -> Clock:
    return _clock
