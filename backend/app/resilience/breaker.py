"""Hand-rolled circuit breaker (~60 lines as SPEC asks)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum


class BreakerState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    recovery_timeout_s: float = 30.0
    half_open_successes: int = 1
    _failures: int = 0
    _half_open_ok: int = 0
    _opened_at: float | None = None
    state: BreakerState = field(default=BreakerState.CLOSED)

    def allow(self) -> bool:
        if self.state == BreakerState.CLOSED:
            return True
        if self.state == BreakerState.OPEN:
            assert self._opened_at is not None
            if time.monotonic() - self._opened_at >= self.recovery_timeout_s:
                self.state = BreakerState.HALF_OPEN
                self._half_open_ok = 0
                return True
            return False
        return True  # half-open: allow a probe

    def record_success(self) -> None:
        if self.state == BreakerState.HALF_OPEN:
            self._half_open_ok += 1
            if self._half_open_ok >= self.half_open_successes:
                self.state = BreakerState.CLOSED
                self._failures = 0
                self._opened_at = None
        else:
            self._failures = 0

    def record_failure(self) -> None:
        if self.state == BreakerState.HALF_OPEN:
            self._trip()
            return
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._trip()

    def _trip(self) -> None:
        self.state = BreakerState.OPEN
        self._opened_at = time.monotonic()
        self._half_open_ok = 0
