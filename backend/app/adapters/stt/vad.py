"""End-of-speech detection.

webrtcvad pulls in a broken pkg_resources path on some Python 3.12 + setuptools
combos, so we use a small energy VAD instead (same role: detect trailing silence
after speech). Recorded in DECISIONS.md.
"""

from __future__ import annotations

import array
import math


class FrameVAD:
    def __init__(
        self,
        *,
        sample_rate: int = 16000,
        energy_threshold: float = 500.0,
        hangover_frames: int = 15,
    ) -> None:
        self.sample_rate = sample_rate
        self.energy_threshold = energy_threshold
        self.hangover_frames = hangover_frames
        self._ring: list[bool] = []
        self.speech_seen = False

    def reset(self) -> None:
        self._ring.clear()
        self.speech_seen = False

    def accept(self, frame_pcm: bytes) -> bool:
        """Return True when end-of-utterance is detected after speech."""
        voiced = self._is_voiced(frame_pcm)
        if voiced:
            self.speech_seen = True
        self._ring.append(voiced)
        if len(self._ring) > self.hangover_frames * 2:
            self._ring.pop(0)
        if not self.speech_seen or len(self._ring) < self.hangover_frames:
            return False
        recent = self._ring[-self.hangover_frames :]
        silence = sum(1 for v in recent if not v)
        return silence >= self.hangover_frames - 3

    def _is_voiced(self, frame_pcm: bytes) -> bool:
        if len(frame_pcm) < 2:
            return False
        samples = array.array("h")
        samples.frombytes(frame_pcm[: len(frame_pcm) - (len(frame_pcm) % 2)])
        if not samples:
            return False
        # RMS energy
        acc = 0.0
        for s in samples:
            acc += float(s) * float(s)
        rms = math.sqrt(acc / len(samples))
        return rms >= self.energy_threshold
