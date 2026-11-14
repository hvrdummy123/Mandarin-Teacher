"""Ordered LLM fallback with breaker + quota checks."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field

import httpx

from app.logging import get_logger
from app.ports.llm import LLMProvider
from app.resilience.breaker import CircuitBreaker
from app.resilience.quota import QuotaTracker
from app.resilience.retry import with_retry

log = get_logger(__name__)

RETRYABLE = (TimeoutError, ConnectionError, httpx.TimeoutException, httpx.TransportError)


class AllProvidersFailed(RuntimeError):
    pass


@dataclass
class FallbackChain:
    providers: Sequence[LLMProvider]
    quota: QuotaTracker = field(default_factory=QuotaTracker)
    breakers: dict[str, CircuitBreaker] = field(default_factory=dict)
    attempts: int = 2

    def _breaker(self, name: str) -> CircuitBreaker:
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker()
        return self.breakers[name]

    def _eligible(self) -> list[LLMProvider]:
        out: list[LLMProvider] = []
        for p in self.providers:
            br = self._breaker(p.name)
            if not br.allow():
                log.info("llm_skip_breaker_open", provider=p.name)
                continue
            if not self.quota.allow(p.name):
                log.info("llm_skip_quota", provider=p.name)
                continue
            out.append(p)
        return out

    async def complete(self, *, system: str, user: str, json_mode: bool = False) -> str:
        errors: list[str] = []
        for provider in self._eligible():
            br = self._breaker(provider.name)

            async def _call(p: LLMProvider = provider) -> str:
                return await p.complete(system=system, user=user, json_mode=json_mode)

            try:
                text = await with_retry(
                    _call,
                    attempts=self.attempts,
                    retry_on=RETRYABLE + (httpx.HTTPStatusError,),
                )
            except Exception as exc:
                # Also treat 429 / 5xx surfaced as HTTPStatusError
                if isinstance(exc, httpx.HTTPStatusError):
                    code = exc.response.status_code
                    if code != 429 and code < 500:
                        errors.append(f"{provider.name}: {exc}")
                        br.record_failure()
                        continue
                br.record_failure()
                errors.append(f"{provider.name}: {exc}")
                log.warning("llm_provider_failed", provider=provider.name, error=str(exc))
                continue
            br.record_success()
            self.quota.record(provider.name, tokens=max(1, len(text) // 4))
            return text
        raise AllProvidersFailed("; ".join(errors) or "no providers available")

    async def stream(self, *, system: str, user: str) -> AsyncIterator[str]:
        """Stream from the first healthy provider; on mid-stream failure, stop (no remix)."""
        errors: list[str] = []
        for provider in self._eligible():
            br = self._breaker(provider.name)
            try:
                got_any = False
                async for chunk in provider.stream(system=system, user=user):
                    got_any = True
                    yield chunk
                if got_any:
                    br.record_success()
                    self.quota.record(provider.name, tokens=1)
                    return
            except Exception as exc:
                br.record_failure()
                errors.append(f"{provider.name}: {exc}")
                log.warning("llm_stream_failed", provider=provider.name, error=str(exc))
                continue
        raise AllProvidersFailed("; ".join(errors) or "no providers available")
