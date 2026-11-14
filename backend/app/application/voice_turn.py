"""Run one voice turn: STT → LLM → TTS; persist audio for later tone scoring."""

from __future__ import annotations

import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from sqlalchemy.orm import Session

from app.adapters.persistence import models as m
from app.adapters.stt.faster_whisper_adapter import FasterWhisperAdapter
from app.adapters.tts.edge import EdgeTTSAdapter
from app.application.chat import ChatServices, _build_reply_prompt, _message_dict, analyse_turn
from app.domain.level import enforce_level_on_reply
from app.domain.topics import get_topic
from app.logging import get_logger

log = get_logger(__name__)

_HAN = re.compile(r"[\u4e00-\u9fff]")


def looks_like_chinese(text: str) -> bool:
    if not text.strip():
        return False
    han = len(_HAN.findall(text))
    return han / max(1, len(text.replace(" ", ""))) >= 0.3


async def run_voice_turn(
    db: Session,
    services: ChatServices,
    *,
    session_id: int,
    pcm: bytes,
    stt: FasterWhisperAdapter,
    tts: EdgeTTSAdapter,
    audio_dir: Path,
    send_json: Callable[[dict[str, object]], Awaitable[None]],
    send_bytes: Callable[[bytes], Awaitable[None]],
    timings_sink: list[dict[str, object]],
) -> None:
    t0 = time.perf_counter()
    session = db.get(m.Session, session_id)
    if session is None:
        await send_json({"type": "error", "detail": "session not found"})
        return

    t_stt0 = time.perf_counter()
    heard = stt.transcribe(pcm)
    stt_ms = int((time.perf_counter() - t_stt0) * 1000)
    if not heard.strip():
        await send_json({"type": "error", "detail": "I did not catch that — try again?"})
        return

    # Persist raw audio for Phase 5 tone scoring.
    audio_dir.mkdir(parents=True, exist_ok=True)
    wav_name = f"turn_{int(time.time() * 1000)}.wav"
    wav_path = audio_dir / wav_name
    wav_path.write_bytes(FasterWhisperAdapter.pcm_to_wav_bytes(pcm))

    topic = get_topic(session.topic_id)
    keywords = set(topic.keywords) if topic else set()
    allowed = services.allowed_for_level(session.level)
    vocab_hint = services.hint_for_level(session.level)

    # If transcript is mostly not Chinese, still show as-is; prompt LLM on meaning.
    user_display = heard
    system = _build_reply_prompt(
        level=session.level,
        topic=topic,
        saved=[],
        vocab_hint=vocab_hint,
    )
    if not looks_like_chinese(heard):
        system += (
            "\nThe learner's last utterance may be broken Chinese mixed with English. "
            "Infer their likely meaning and reply helpfully in simple Chinese."
        )

    user_tokens = services.analyzer.tokens_as_dicts(user_display)
    user_msg = m.Message(
        session_id=session.id,
        role="user",
        text=user_display,
        pinyin_json=user_tokens,
        translation=None,
        audio_path=str(wav_path),
    )
    db.add(user_msg)
    db.flush()

    # Attach heard_raw on the wire for the UI (same as text when clean).
    user_payload = _message_dict(user_msg, None)
    user_payload["heard_raw"] = heard
    user_payload["audio_path"] = str(wav_path)
    await send_json({"type": "transcript.user", "message": user_payload})

    t_llm0 = time.perf_counter()
    try:
        first = await services.llm.complete(system=system, user=heard, json_mode=False)
    except Exception as exc:
        await send_json({"type": "error", "detail": f"LLM failed: {exc}"})
        return
    llm_first_ms = int((time.perf_counter() - t_llm0) * 1000)

    async def _regen(forbidden: list[str]) -> str:
        sys2 = _build_reply_prompt(
            level=session.level,
            topic=topic,
            saved=[],
            vocab_hint=vocab_hint,
            forbidden=forbidden,
        )
        return await services.llm.complete(system=sys2, user=heard, json_mode=False)

    checked = await enforce_level_on_reply(
        _regen,
        first_reply=first,
        allowed=allowed,
        keywords=keywords,
        threshold=services.out_of_vocab_threshold,
    )
    reply = checked.text

    analysis = await analyse_turn(
        services,
        level=session.level,
        topic=topic,
        user_text=heard,
        reply_text=reply,
    )
    if analysis.translation_en:
        user_msg.translation = analysis.translation_en
    if analysis.correction is not None:
        db.add(
            m.Correction(
                message_id=user_msg.id,
                original=heard,
                better=analysis.correction.better,
                reason=analysis.correction.reason,
            )
        )

    reply_tokens = services.analyzer.tokens_as_dicts(reply, out_of_level=set(checked.out_of_level))
    assistant_msg = m.Message(
        session_id=session.id,
        role="assistant",
        text=reply,
        pinyin_json=reply_tokens,
        translation=analysis.reply_translation_en or None,
    )
    db.add(assistant_msg)
    db.flush()

    await send_json(
        {
            "type": "reply.sentence",
            "text": reply,
            "message": _message_dict(assistant_msg, None),
        }
    )
    await send_json({"type": "analysis", "analysis": analysis.model_dump()})

    t_tts0 = time.perf_counter()
    tts_first_ms: int | None = None
    async for mp3 in tts.stream_sentences(reply):
        if tts_first_ms is None:
            tts_first_ms = int((time.perf_counter() - t_tts0) * 1000)
        await send_bytes(mp3)

    total_ms = int((time.perf_counter() - t0) * 1000)
    timing: dict[str, object] = {
        "stt_ms": stt_ms,
        "llm_first_token_ms": llm_first_ms,
        "tts_first_byte_ms": tts_first_ms,
        "total_ms": total_ms,
        "session_id": session_id,
    }
    timings_sink.append(timing)
    if len(timings_sink) > 50:
        del timings_sink[:-50]
    log.info("voice_turn_timing", **timing)
    await send_json({"type": "turn.end"})
