"""Energy VAD end-of-speech detection."""

from __future__ import annotations

import array
import math

from app.adapters.stt.vad import FrameVAD
from app.application.voice_turn import looks_like_chinese


def _frame(rms: float, n: int = 320) -> bytes:
    amp = int(min(20000, rms * math.sqrt(2)))
    samples = array.array("h", [amp if i % 2 == 0 else -amp for i in range(n)])
    return samples.tobytes()


def test_vad_detects_end_after_speech() -> None:
    vad = FrameVAD(energy_threshold=500.0, hangover_frames=10)
    # Loud frames = speech
    for _ in range(5):
        assert vad.accept(_frame(2000.0)) is False
    assert vad.speech_seen is True
    # Silence hangover
    ended = False
    for _ in range(20):
        if vad.accept(_frame(0.0)):
            ended = True
            break
    assert ended is True


def test_looks_like_chinese() -> None:
    assert looks_like_chinese("我想喝 coffee") is True
    assert looks_like_chinese("hello there") is False
