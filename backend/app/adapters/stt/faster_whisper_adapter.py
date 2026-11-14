"""Local faster-whisper STT.

Language is *not* forced to zh: mixed Mandarin/English speech is common for
this learner. We leave language=None (auto) and bias with a Chinese initial_prompt.
"""

from __future__ import annotations

import io
import platform
import wave
from pathlib import Path

import numpy as np

from app.logging import get_logger

log = get_logger(__name__)

# Bias toward Mandarin without forbidding English words.
_INITIAL_PROMPT = "这是一段中文口语练习，可能夹杂一点英文单词。你好，我想点菜，coffee，谢谢。"


def _pick_device(requested: str) -> tuple[str, str]:
    """Return (device, compute_type). MPS needs float16/float32, not int8."""
    req = (requested or "auto").lower()
    if req == "cpu":
        return "cpu", "int8"
    if req == "mps":
        return "mps", "float16"
    # auto: prefer Apple Silicon MPS when available
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return "mps", "float16"
    return "cpu", "int8"


class FasterWhisperAdapter:
    name = "faster-whisper"

    def __init__(
        self,
        *,
        model_size: str = "base",
        compute_type: str = "int8",
        device: str = "auto",
        download_root: Path | None = None,
    ) -> None:
        self.model_size = model_size
        self.compute_type = compute_type
        self.device_pref = device
        self.download_root = download_root
        self._model = None
        self.loaded = False
        self.device_used = "cpu"
        self._topic_bias = ""

    def set_topic_bias(self, keywords: str) -> None:
        """Extra words for Whisper initial_prompt (topic vocabulary)."""
        self._topic_bias = keywords.strip()

    def load(self) -> None:
        if self._model is not None:
            return
        from faster_whisper import WhisperModel

        device, auto_compute = _pick_device(self.device_pref)
        # Honour explicit compute_type on CPU; MPS ignores int8.
        compute = auto_compute if device == "mps" else self.compute_type
        log.info(
            "whisper_loading",
            size=self.model_size,
            device=device,
            compute=compute,
        )
        try:
            self._model = WhisperModel(
                self.model_size,
                device=device,
                compute_type=compute,
                download_root=str(self.download_root) if self.download_root else None,
            )
            self.device_used = device
        except Exception as exc:
            if device != "cpu":
                log.warning("whisper_device_fallback", wanted=device, error=str(exc))
                self._model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type=self.compute_type,
                    download_root=str(self.download_root) if self.download_root else None,
                )
                self.device_used = "cpu"
            else:
                raise
        self.loaded = True
        log.info("whisper_loaded", device=self.device_used)

    def transcribe(self, pcm_16k_mono: bytes, *, sample_rate: int = 16000) -> str:
        self.load()
        assert self._model is not None
        audio = np.frombuffer(pcm_16k_mono, dtype=np.int16).astype(np.float32) / 32768.0
        prompt = _INITIAL_PROMPT
        if self._topic_bias:
            prompt = f"{_INITIAL_PROMPT} 本话题常用词：{self._topic_bias}。"
        segments, _info = self._model.transcribe(
            audio,
            language=None,  # auto-detect; Chinese-biased via initial_prompt
            task="transcribe",
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
            initial_prompt=prompt,
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
