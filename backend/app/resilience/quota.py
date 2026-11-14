"""Per-provider daily quota tracker (in-memory; DB table fills in later)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class QuotaTracker:
    """Blocks a provider once requests or tokens hit the free-tier ceiling."""

    daily_request_limit: int = 200
    daily_token_limit: int = 200_000
    _by_day: dict[tuple[str, date], dict[str, int]] = field(default_factory=dict)

    def _bucket(self, provider: str, day: date | None = None) -> dict[str, int]:
        key = (provider, day or date.today())
        if key not in self._by_day:
            self._by_day[key] = {"requests": 0, "tokens": 0}
        return self._by_day[key]

    def allow(self, provider: str, *, day: date | None = None) -> bool:
        b = self._bucket(provider, day)
        return b["requests"] < self.daily_request_limit and b["tokens"] < self.daily_token_limit

    def record(self, provider: str, *, tokens: int = 0, day: date | None = None) -> None:
        b = self._bucket(provider, day)
        b["requests"] += 1
        b["tokens"] += max(0, tokens)
