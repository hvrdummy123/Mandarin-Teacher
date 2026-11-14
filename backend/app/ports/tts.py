from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable


@runtime_checkable
class TTSProvider(Protocol):
    name: str

    async def synthesize(self, text: str, *, rate: str = "+0%") -> bytes:
        """Return complete MP3 bytes."""
        ...

    def stream_sentences(self, text: str, *, rate: str = "+0%") -> AsyncIterator[bytes]: ...
