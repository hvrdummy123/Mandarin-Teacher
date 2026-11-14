"""Local faster-whisper STT.

Language is *not* forced to zh: mixed Mandarin/English speech is common for
this learner. We leave language=None (auto) and bias with a Chinese initial_prompt.
"""

from __future__ import annotations

import io
import wave
from pathlib import Path

import numpy as np

from app.logging import get_logger

log = get_logger(__name__)

# Bias toward Mandarin without forbidding English words.
_INITIAL_PROMPT = "这是一段中文口语练习，可能夹杂一点英文单词。你好，我想点菜，coffee，谢谢。"


class FasterWhisperAdapter:
    name = "faster-whisper"

    def __init__(
        self,
        *,
        model_size: str = "small",
        compute_type: str = "int8",
        download_root: Path | None = None,
    ) -> None:
        self.model_size = model_size
        self.compute_type = compute_type
        self.download_root = download_root
        self._model = None
        self.loaded = False

    def load(self) -> None:
        if self._model is not None:
            return
        from faster_whisper import WhisperModel

        log.info("whisper_loading", size=self.model_size, compute=self.compute_type)
        self._model = WhisperModel(
            self.model_size,
            device="cpu",
            compute_type=self.compute_type,
            download_root=str(self.download_root) if self.download_root else None,
        )
        self.loaded = True
        log.info("whisper_loaded")

    def transcribe(self, pcm_16k_mono: bytes, *, sample_rate: int = 16000) -> str:
        self.load()
        assert self._model is not None
        audio = np.frombuffer(pcm_16k_mono, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _info = self._model.transcribe(
            audio,
            language=None,  # auto-detect; Chinese-biased via initial_prompt
            task="transcribe",
            beam_size=1,
            vad_filter=False,
            initial_prompt=_INITIAL_PROMPT,
        )
        text = "".join(seg.text for seg in segments).strip()
        return text

    @staticmethod
    def pcm_to_wav_bytes(pcm: bytes, sample_rate: int = 16000) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(pcm)
        return buf.getvalue()
