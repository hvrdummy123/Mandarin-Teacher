from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class STTProvider(Protocol):
    name: str

    def transcribe(self, pcm_16k_mono: bytes, *, sample_rate: int = 16000) -> str: ...
