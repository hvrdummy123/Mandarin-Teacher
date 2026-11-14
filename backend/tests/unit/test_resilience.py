"""Retry, breaker, quota, fallback chain."""

from __future__ import annotations

from datetime import date

import httpx
import pytest

from app.adapters.llm.fake import FakeLLM
from app.adapters.llm.fallback import AllProvidersFailed, FallbackChain
from app.resilience.breaker import BreakerState, CircuitBreaker
from app.resilience.quota import QuotaTracker
from app.resilience.retry import with_retry


@pytest.mark.asyncio
async def test_retry_backoff_eventually_succeeds() -> None:
    n = {"i": 0}

    async def flaky() -> str:
        n["i"] += 1
        if n["i"] < 3:
            raise TimeoutError("nope")
        return "ok"

    assert await with_retry(flaky, attempts=3, base_delay_s=0.01) == "ok"
    assert n["i"] == 3


def test_circuit_breaker_states() -> None:
    br = CircuitBreaker(failure_threshold=2, recovery_timeout_s=0.0)
    assert br.state == BreakerState.CLOSED
    br.record_failure()
    assert br.state == BreakerState.CLOSED
    br.record_failure()
    assert br.state == BreakerState.OPEN
    assert br.allow() is True  # recovery_timeout 0 → half-open
    assert br.state == BreakerState.HALF_OPEN
    br.record_success()
    assert br.state == BreakerState.CLOSED


def test_quota_blocks_at_limit() -> None:
    q = QuotaTracker(daily_request_limit=2, daily_token_limit=1000)
    day = date(2026, 1, 1)
    assert q.allow("gemini", day=day)
    q.record("gemini", tokens=10, day=day)
    q.record("gemini", tokens=10, day=day)
    assert q.allow("gemini", day=day) is False


@pytest.mark.asyncio
async def test_fallback_moves_on_timeout() -> None:
    primary = FakeLLM(name="a", fail_times=2, fail_with=TimeoutError)
    secondary = FakeLLM(name="b", reply_text="从备用来的")
    chain = FallbackChain(providers=[primary, secondary], attempts=1)
    text = await chain.complete(system="s", user="u")
    assert text == "从备用来的"


@pytest.mark.asyncio
async def test_fallback_on_429() -> None:
    class Boom(FakeLLM):
        async def complete(self, *, system: str, user: str, json_mode: bool = False) -> str:
            req = httpx.Request("POST", "https://example.com")
            resp = httpx.Response(429, request=req)
            raise httpx.HTTPStatusError("rate limited", request=req, response=resp)

    chain = FallbackChain(
        providers=[Boom(name="a"), FakeLLM(name="b", reply_text="ok")],
        attempts=1,
    )
    assert await chain.complete(system="s", user="u") == "ok"


@pytest.mark.asyncio
async def test_fallback_all_fail() -> None:
    chain = FallbackChain(
        providers=[
            FakeLLM(name="a", fail_times=5, fail_with=TimeoutError),
            FakeLLM(name="b", fail_times=5, fail_with=TimeoutError),
        ],
        attempts=1,
    )
    with pytest.raises(AllProvidersFailed):
        await chain.complete(system="s", user="u")


@pytest.mark.asyncio
async def test_fallback_force_probe_when_all_breakers_open() -> None:
    """User must not get stuck with 'no providers available' forever."""
    primary = FakeLLM(name="a", reply_text="recovered")
    chain = FallbackChain(providers=[primary], attempts=1)
    br = chain._breaker("a")
    br.record_failure()
    br.record_failure()
    assert br.state == BreakerState.OPEN
    # Recovery timeout still running — _eligible should force a half-open probe.
    text = await chain.complete(system="s", user="u")
    assert text == "recovered"
    assert br.state == BreakerState.CLOSED
