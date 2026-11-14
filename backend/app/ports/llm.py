"""LLM provider port."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    async def complete(self, *, system: str, user: str, json_mode: bool = False) -> str:
        """Non-streaming completion."""
        ...

    def stream(self, *, system: str, user: str) -> AsyncIterator[str]:
        """Yield text deltas for the reply path."""
        ...
