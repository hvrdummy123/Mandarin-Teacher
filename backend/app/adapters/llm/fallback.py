"""Ordered LLM fallback with breaker + quota checks."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field

import httpx

from app.logging import get_logger
from app.ports.llm import LLMProvider
from app.resilience.breaker import BreakerState, CircuitBreaker
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
    # One attempt — free tiers 429 quickly; retries just burn the quota window.
    attempts: int = 1

    def _breaker(self, name: str) -> CircuitBreaker:
        if name not in self.breakers:
            # Trip after 2 failures; recover after 45s. Never block forever —
            # _eligible forces a probe when every breaker is open.
            self.breakers[name] = CircuitBreaker(
                failure_threshold=2,
                recovery_timeout_s=45.0,
            )
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
        if out:
            return out
        # All breakers open / quota blocked — force one probe so the user is not stuck.
        forced: list[LLMProvider] = []
        for p in self.providers:
            if not self.quota.allow(p.name):
                continue
            br = self._breaker(p.name)
            br.state = BreakerState.HALF_OPEN
            br._half_open_ok = 0
            log.info("llm_force_probe", provider=p.name)
            forced.append(p)
        return forced

    async def complete(self, *, system: str, user: str, json_mode: bool = False) -> str:
        errors: list[str] = []
        eligible = self._eligible()
        if not eligible:
            raise AllProvidersFailed(
                "All AI providers are rate-limited right now. Wait ~30s and tap the mic again."
            )
        for provider in eligible:
            br = self._breaker(provider.name)

            async def _call(p: LLMProvider = provider) -> str:
                return await p.complete(system=system, user=user, json_mode=json_mode)

            try:
                text = await with_retry(
                    _call,
                    attempts=self.attempts,
                    retry_on=RETRYABLE,
                )
            except httpx.HTTPStatusError as exc:
                code = exc.response.status_code
                errors.append(f"{provider.name}: {exc}")
                if code in {401, 403, 404}:
                    log.warning("llm_provider_skip", provider=provider.name, status=code)
                    continue
                br.record_failure()
                log.warning("llm_provider_failed", provider=provider.name, error=str(exc))
                continue
            except Exception as exc:
                br.record_failure()
                errors.append(f"{provider.name}: {exc}")
                log.warning("llm_provider_failed", provider=provider.name, error=str(exc))
                continue
            br.record_success()
            self.quota.record(provider.name, tokens=max(1, len(text) // 4))
            return text
        raise AllProvidersFailed(
            "; ".join(errors)
            or "All AI providers are rate-limited right now. Wait ~30s and tap the mic again."
        )

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
