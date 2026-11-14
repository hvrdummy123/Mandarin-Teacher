"""Bounded retries with exponential backoff and jitter."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def with_retry(
    fn: Callable[[], Awaitable[T]],
    *,
    attempts: int = 3,
    base_delay_s: float = 0.2,
    max_delay_s: float = 2.0,
    retry_on: tuple[type[BaseException], ...] = (TimeoutError, ConnectionError),
) -> T:
    last: BaseException | None = None
    for i in range(attempts):
        try:
            return await fn()
        except retry_on as exc:
            last = exc
            if i == attempts - 1:
                break
            delay = min(max_delay_s, base_delay_s * (2**i))
            delay *= 0.5 + random.random()  # jitter
            await asyncio.sleep(delay)
    assert last is not None
    raise last
