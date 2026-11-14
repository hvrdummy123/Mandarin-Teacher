"""edge-tts with on-disk MP3 cache."""

from __future__ import annotations

import hashlib
import re
from collections.abc import AsyncIterator
from pathlib import Path

import edge_tts

from app.logging import get_logger

log = get_logger(__name__)

_SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;])")


class EdgeTTSAdapter:
    name = "edge-tts"

    def __init__(self, *, voice: str, cache_dir: Path) -> None:
        self.voice = voice
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, text: str, rate: str) -> Path:
        key = hashlib.sha256(f"{self.voice}|{rate}|{text}".encode()).hexdigest()
        return self.cache_dir / f"{key}.mp3"

    async def synthesize(self, text: str, *, rate: str = "+0%") -> bytes:
        text = text.strip()
        if not text:
            return b""
        path = self._cache_path(text, rate)
        if path.is_file():
            return path.read_bytes()
        communicate = edge_tts.Communicate(text, self.voice, rate=rate)
        chunks: list[bytes] = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        data = b"".join(chunks)
        path.write_bytes(data)
        return data

    async def stream_sentences(self, text: str, *, rate: str = "+0%") -> AsyncIterator[bytes]:
        parts = [p.strip() for p in _SENTENCE_SPLIT.split(text) if p and p.strip()]
        if not parts:
            parts = [text.strip()] if text.strip() else []
        for part in parts:
            audio = await self.synthesize(part, rate=rate)
            if audio:
                yield audio
