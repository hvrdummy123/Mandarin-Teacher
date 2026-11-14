#!/usr/bin/env python3
"""Generate short 16 kHz mono WAV fixtures via edge-tts (+ ffmpeg).

Fixtures:
  clean_zh.wav   — a clean Chinese sentence
  mixed_zh_en.wav — Chinese mixed with English words

Also writes fixtures.json with expected transcripts for CER checks.

Usage:
  PYTHONPATH=backend uv run python scripts/gen_audio_fixtures.py
  PYTHONPATH=backend uv run python scripts/gen_audio_fixtures.py --check
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
import time
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

OUT_DIR = REPO / "backend" / "tests" / "e2e_audio" / "fixtures"

# Reference texts (what we ask TTS to speak). CER is measured against these.
FIXTURES: list[dict[str, str]] = [
    {
        "id": "clean_zh",
        "text": "你好，我想点一份牛肉面，谢谢。",
        "filename": "clean_zh.wav",
        "note": "clean Chinese sentence",
    },
    {
        "id": "mixed_zh_en",
        "text": "我想要一杯 coffee，可以吗？谢谢。",
        "filename": "mixed_zh_en.wav",
        "note": "Chinese mixed with English word",
    },
]


def _normalize_for_cer(s: str) -> str:
    """Strip spaces/punct for Chinese CER; keep Latin letters case-folded."""
    keep: list[str] = []
    for ch in s:
        if "\u4e00" <= ch <= "\u9fff":
            keep.append(ch)
        elif ch.isalpha() or ch.isdigit():
            keep.append(ch.lower())
    return "".join(keep)


def cer(reference: str, hypothesis: str) -> float:
    """Character error rate = edit distance / len(reference)."""
    ref = _normalize_for_cer(reference)
    hyp = _normalize_for_cer(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    # Levenshtein
    prev = list(range(len(hyp) + 1))
    for i, rc in enumerate(ref, start=1):
        cur = [i]
        for j, hc in enumerate(hyp, start=1):
            ins = cur[j - 1] + 1
            delete = prev[j] + 1
            sub = prev[j - 1] + (0 if rc == hc else 1)
            cur.append(min(ins, delete, sub))
        prev = cur
    return prev[-1] / len(ref)


def wav_duration_s(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / float(wf.getframerate())


def wav_to_pcm(path: Path) -> tuple[bytes, int]:
    with wave.open(str(path), "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getsampwidth() == 2
        rate = wf.getframerate()
        return wf.readframes(wf.getnframes()), rate


async def _synthesize_mp3(text: str, voice: str, mp3_path: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(mp3_path))


def _mp3_to_wav_16k(mp3_path: Path, wav_path: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(mp3_path),
        "-ac",
        "1",
        "-ar",
        "16000",
        "-sample_fmt",
        "s16",
        str(wav_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)


async def generate(voice: str) -> list[dict[str, object]]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta: list[dict[str, object]] = []
    for item in FIXTURES:
        mp3 = OUT_DIR / f"{item['id']}.mp3"
        wav = OUT_DIR / item["filename"]
        print(f"TTS → {item['filename']}: {item['text']}")
        await _synthesize_mp3(item["text"], voice, mp3)
        _mp3_to_wav_16k(mp3, wav)
        mp3.unlink(missing_ok=True)
        dur = wav_duration_s(wav)
        entry = {
            **item,
            "path": str(wav.relative_to(REPO)),
            "duration_s": round(dur, 3),
            "sample_rate": 16000,
        }
        meta.append(entry)
        print(f"  wrote {wav} ({dur:.2f}s)")
    manifest = OUT_DIR / "fixtures.json"
    manifest.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"manifest → {manifest}")
    return meta


def run_stt_check(meta: list[dict[str, object]]) -> int:
    from app.config import get_settings
    from app.adapters.stt.faster_whisper_adapter import FasterWhisperAdapter

    settings = get_settings()
    stt = FasterWhisperAdapter(
        model_size=settings.whisper_model_size,
        compute_type=settings.whisper_compute_type,
        download_root=Path(settings.data_dir) / "whisper",
    )
    print(
        f"\nLoading Whisper model={settings.whisper_model_size} "
        f"compute={settings.whisper_compute_type} (no mocks)…"
    )
    t_load0 = time.perf_counter()
    stt.load()
    load_ms = int((time.perf_counter() - t_load0) * 1000)
    print(f"Whisper loaded in {load_ms} ms (loaded={stt.loaded})")

    failures = 0
    print("\n=== STT check ===")
    for item in meta:
        path = REPO / str(item["path"])
        pcm, rate = wav_to_pcm(path)
        assert rate == 16000
        t0 = time.perf_counter()
        hyp = stt.transcribe(pcm, sample_rate=rate)
        stt_ms = int((time.perf_counter() - t0) * 1000)
        ref = str(item["text"])
        score = cer(ref, hyp)
        ok = score <= 0.15
        status = "PASS" if ok else "FAIL"
        if not ok:
            failures += 1
        print(f"[{status}] {item['id']}")
        print(f"  reference : {ref}")
        print(f"  transcript: {hyp}")
        print(f"  CER       : {score:.3f}  (budget ≤ 0.15)")
        print(f"  STT time  : {stt_ms} ms  (duration {item['duration_s']}s)")
    return 1 if failures else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="After generating, load real faster-whisper and print CER / STT ms",
    )
    parser.add_argument(
        "--voice",
        default=None,
        help="edge-tts voice (default: TTS_VOICE from settings)",
    )
    args = parser.parse_args()

    from app.config import get_settings

    voice = args.voice or get_settings().tts_voice
    meta = asyncio.run(generate(voice))
    if args.check:
        return run_stt_check(meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
