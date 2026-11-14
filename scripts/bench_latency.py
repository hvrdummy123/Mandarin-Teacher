#!/usr/bin/env python3
"""Voice-turn latency bench: p50/p95 for STT, LLM, TTS, end-of-speech→first audio.

Runs N turns on fixture WAVs. By default uses the real configured Whisper, TTS,
and LLM (no mocks). Pass --fake-llm to isolate local STT/TTS costs per SPEC §15.

Usage:
  PYTHONPATH=backend uv run python scripts/bench_latency.py
  PYTHONPATH=backend uv run python scripts/bench_latency.py --runs 20
  PYTHONPATH=backend uv run python scripts/bench_latency.py --fake-llm
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
import wave
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "backend"))

FIXTURES_DIR = REPO / "backend" / "tests" / "e2e_audio" / "fixtures"


def percentile(values: list[float], p: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    k = (len(ordered) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    if f == c:
        return ordered[f]
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def wav_to_pcm(path: Path) -> bytes:
    with wave.open(str(path), "rb") as wf:
        assert wf.getnchannels() == 1 and wf.getsampwidth() == 2
        return wf.readframes(wf.getnframes())


def load_fixture_pcm() -> tuple[Path, bytes]:
    manifest = FIXTURES_DIR / "fixtures.json"
    if not manifest.is_file():
        raise SystemExit(
            f"Missing {manifest}. Run: PYTHONPATH=backend uv run python scripts/gen_audio_fixtures.py"
        )
    items = json.loads(manifest.read_text(encoding="utf-8"))
    # Prefer clean Chinese for stable timing; fall back to first entry.
    chosen = next((i for i in items if i.get("id") == "clean_zh"), items[0])
    path = REPO / chosen["path"]
    if not path.is_file():
        raise SystemExit(f"Fixture WAV missing: {path}")
    return path, wav_to_pcm(path)


async def one_turn(
    *,
    pcm: bytes,
    stt: object,
    tts: object,
    llm: object,
) -> dict[str, float]:
    """Measure stages without the full WS stack (same adapters as production)."""
    t_eos = time.perf_counter()  # treat buffer ready as end-of-speech

    t0 = time.perf_counter()
    heard = stt.transcribe(pcm)  # type: ignore[attr-defined]
    stt_ms = (time.perf_counter() - t0) * 1000.0
    if not heard.strip():
        raise RuntimeError("empty STT transcript")

    t1 = time.perf_counter()
    reply = await llm.complete(  # type: ignore[attr-defined]
        system="You are a Mandarin tutor. Reply in 1 short Chinese sentence.",
        user=heard,
        json_mode=False,
    )
    llm_first_ms = (time.perf_counter() - t1) * 1000.0
    if not reply.strip():
        reply = "好的，请再说一次。"

    t2 = time.perf_counter()
    tts_first_ms: float | None = None
    async for _chunk in tts.stream_sentences(reply):  # type: ignore[attr-defined]
        if tts_first_ms is None:
            tts_first_ms = (time.perf_counter() - t2) * 1000.0
        break
    if tts_first_ms is None:
        tts_first_ms = (time.perf_counter() - t2) * 1000.0

    eos_to_audio_ms = (time.perf_counter() - t_eos) * 1000.0
    # More precisely: STT + LLM + TTS first byte from EOS
    eos_to_audio_ms = stt_ms + llm_first_ms + tts_first_ms

    return {
        "stt_ms": stt_ms,
        "llm_first_token_ms": llm_first_ms,
        "tts_first_byte_ms": tts_first_ms,
        "eos_to_first_audio_ms": eos_to_audio_ms,
    }


def print_stats(name: str, values: list[float], budget_ms: float | None = None) -> None:
    p50 = percentile(values, 50)
    p95 = percentile(values, 95)
    mean = statistics.fmean(values) if values else float("nan")
    budget = ""
    if budget_ms is not None:
        flag = "OK" if p95 <= budget_ms else "OVER"
        budget = f"  budget_p95≤{budget_ms:.0f}ms → {flag}"
    print(f"{name:24s}  n={len(values):2d}  p50={p50:8.1f}  p95={p95:8.1f}  mean={mean:8.1f}{budget}")


async def async_main(args: argparse.Namespace) -> int:
    from app.adapters.llm.fake import FakeLLM
    from app.adapters.stt.faster_whisper_adapter import FasterWhisperAdapter
    from app.adapters.tts.edge import EdgeTTSAdapter
    from app.config import get_settings
    from app.container import build_llm_chain

    settings = get_settings()
    path, pcm = load_fixture_pcm()
    print(f"Fixture: {path} ({len(pcm) // 32} ms of 16 kHz PCM)")
    print(
        f"Whisper: size={settings.whisper_model_size} compute={settings.whisper_compute_type}"
    )

    stt = FasterWhisperAdapter(
        model_size=settings.whisper_model_size,
        compute_type=settings.whisper_compute_type,
        download_root=Path(settings.data_dir) / "whisper",
    )
    print("Loading Whisper (real, no mock)…")
    t0 = time.perf_counter()
    stt.load()
    print(f"Whisper ready in {int((time.perf_counter() - t0) * 1000)} ms")

    tts = EdgeTTSAdapter(voice=settings.tts_voice, cache_dir=Path(settings.tts_cache_dir))

    if args.fake_llm:
        llm: object = FakeLLM(reply_text="好的，你想吃什么？")
        mode = "fake-llm (local STT/TTS isolation)"
    else:
        chain = build_llm_chain(settings)
        if not chain.providers:
            print("FAIL: no LLM providers configured; use --fake-llm or set API keys")
            return 1
        llm = chain
        mode = f"real LLM ({', '.join(p.name for p in chain.providers)})"
    print(f"Mode: {mode}; runs={args.runs}")

    rows: list[dict[str, float]] = []
    for i in range(args.runs):
        print(f"  turn {i + 1}/{args.runs}…", flush=True)
        row = await one_turn(pcm=pcm, stt=stt, tts=tts, llm=llm)
        rows.append(row)
        print(
            f"    stt={row['stt_ms']:.0f} llm={row['llm_first_token_ms']:.0f} "
            f"tts={row['tts_first_byte_ms']:.0f} eos→audio={row['eos_to_first_audio_ms']:.0f} ms"
        )

    print("\n=== Latency summary (ms) ===")
    print_stats("stt_ms", [r["stt_ms"] for r in rows], budget_ms=1500)
    print_stats("llm_first_token_ms", [r["llm_first_token_ms"] for r in rows], budget_ms=1500)
    print_stats("tts_first_byte_ms", [r["tts_first_byte_ms"] for r in rows], budget_ms=None)
    print_stats(
        "eos_to_first_audio_ms",
        [r["eos_to_first_audio_ms"] for r in rows],
        budget_ms=3000,
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=20, help="Number of voice turns (default 20)")
    parser.add_argument(
        "--fake-llm",
        action="store_true",
        help="Use FakeLLM to isolate local STT/TTS (SPEC default assertion path)",
    )
    args = parser.parse_args()
    return asyncio.run(async_main(args))


if __name__ == "__main__":
    raise SystemExit(main())
