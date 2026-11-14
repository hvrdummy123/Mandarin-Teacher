"""Run one voice turn: STT → LLM → TTS (+ analysis in parallel).

Commits DB rows before long awaits so SQLite is not locked during LLM/TTS.
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

from sqlalchemy.orm import Session

from app.adapters.persistence import models as m
from app.adapters.stt.faster_whisper_adapter import FasterWhisperAdapter
from app.adapters.tts.edge import EdgeTTSAdapter
from app.application.chat import ChatServices, _build_reply_prompt, _message_dict, analyse_turn
from app.domain.level import share_out_of_level
from app.domain.topics import get_topic
from app.logging import get_logger

log = get_logger(__name__)

_HAN = re.compile(r"[\u4e00-\u9fff]")


def looks_like_chinese(text: str) -> bool:
    if not text.strip():
        return False
    han = len(_HAN.findall(text))
    return han / max(1, len(text.replace(" ", ""))) >= 0.3


def rough_gloss(tokens: list[dict[str, object]]) -> str:
    """Instant English line from dictionary senses (refined later by analysis)."""
    bits: list[str] = []
    for tok in tokens:
        surface = str(tok.get("surface") or "")
        defs = tok.get("definitions")
        if isinstance(defs, list) and defs and isinstance(defs[0], str):
            sense = defs[0].split("/")[0].strip()
            if sense:
                bits.append(sense)
                continue
        if surface.strip():
            bits.append(surface)
    return " ".join(bits)


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
    heard_hint: str | None = None,
) -> None:
    t0 = time.perf_counter()
    session = db.get(m.Session, session_id)
    if session is None:
        await send_json({"type": "error", "detail": "session not found"})
        return

    if len(pcm) < 16000 * 2 * 0.3:  # < ~300 ms of audio
        await send_json(
            {
                "type": "error",
                "detail": "That was too short — tap the mic, speak, then tap again when done.",
            }
        )
        return

    from app.application.transcript_repair import repair_transcript

    topic = get_topic(session.topic_id)

    hint = (heard_hint or "").strip()
    t_stt0 = time.perf_counter()
    if hint and (looks_like_chinese(hint) or len(hint) >= 2):
        heard = hint
        stt_ms = int((time.perf_counter() - t_stt0) * 1000)
        log.info("stt_used_browser_hint", chars=len(heard))
    else:
        # Bias Whisper with topic keywords when we must run it.
        if topic and topic.keywords:
            stt.set_topic_bias("、".join(topic.keywords[:8]))
        heard = stt.transcribe(pcm)
        stt_ms = int((time.perf_counter() - t_stt0) * 1000)
    if not heard.strip():
        await send_json({"type": "error", "detail": "I did not catch that — try again?"})
        return

    repaired = repair_transcript(heard, topic=topic)
    if repaired.changed:
        log.info("transcript_repaired", before=heard, after=repaired.text, note=repaired.note)
        heard = repaired.text

    audio_dir.mkdir(parents=True, exist_ok=True)
    wav_name = f"turn_{int(time.time() * 1000)}.wav"
    wav_path = audio_dir / wav_name
    wav_path.write_bytes(FasterWhisperAdapter.pcm_to_wav_bytes(pcm))
    keywords = set(topic.keywords) if topic else set()
    allowed = services.allowed_for_level(session.level)
    vocab_hint = services.hint_for_level(session.level)
    level = session.level

    system = _build_reply_prompt(
        level=level,
        topic=topic,
        saved=[],
        vocab_hint=vocab_hint,
    )
    if not looks_like_chinese(heard):
        system += (
            "\nThe learner's last utterance may be broken Chinese mixed with English. "
            "Infer their likely meaning and reply helpfully in simple Chinese."
        )

    user_tokens = services.analyzer.tokens_as_dicts(heard)
    interim_en = rough_gloss(user_tokens) or None
    user_msg = m.Message(
        session_id=session.id,
        role="user",
        text=heard,
        pinyin_json=user_tokens,
        translation=interim_en,
        audio_path=str(wav_path),
    )
    db.add(user_msg)
    db.flush()
    user_id = user_msg.id
    user_payload = _message_dict(user_msg, None)
    user_payload["heard_raw"] = heard
    user_payload["audio_path"] = str(wav_path)
    # Release the write lock before the slow LLM call.
    db.commit()

    await send_json({"type": "transcript.user", "message": user_payload})

    from app.adapters.llm.fallback import AllProvidersFailed

    # Give the model recent turns so it stays in topic / conversation context.
    prior = (
        db.query(m.Message)
        .filter(m.Message.session_id == session_id, m.Message.id != user_id)
        .order_by(m.Message.id.desc())
        .limit(8)
        .all()
    )
    prior.reverse()
    history_lines = [f"{row.role}: {row.text}" for row in prior]
    llm_user = heard
    if history_lines:
        llm_user = (
            "Recent conversation (stay in this context):\n"
            + "\n".join(history_lines)
            + f"\n\nLearner just said: {heard}"
        )

    t_llm0 = time.perf_counter()
    try:
        reply = await services.llm.complete(system=system, user=llm_user, json_mode=False)
    except AllProvidersFailed as exc:
        await send_json(
            {
                "type": "error",
                "detail": (
                    "AI is rate-limited right now (free-tier 429). "
                    "Your line was saved — wait ~30–60s and try again. "
                    f"({exc})"
                ),
            }
        )
        return
    except Exception as exc:
        await send_json(
            {
                "type": "error",
                "detail": f"AI unavailable: {exc}. Your line was saved — tap mic to try again.",
            }
        )
        return
    llm_first_ms = int((time.perf_counter() - t_llm0) * 1000)

    _share, bad = share_out_of_level(reply, allowed=allowed, keywords=keywords)
    out_words = set(bad)
    reply_tokens = services.analyzer.tokens_as_dicts(reply, out_of_level=out_words)
    assistant_msg = m.Message(
        session_id=session_id,
        role="assistant",
        text=reply,
        pinyin_json=reply_tokens,
        translation=None,
    )
    db.add(assistant_msg)
    db.flush()
    assistant_id = assistant_msg.id
    assistant_payload = _message_dict(assistant_msg, None)
    db.commit()

    await send_json(
        {
            "type": "reply.sentence",
            "text": reply,
            "message": assistant_payload,
        }
    )

    from app.domain.correction import AnalysisResult

    analysis_task: asyncio.Task[AnalysisResult] = asyncio.create_task(
        analyse_turn(
            services,
            level=level,
            topic=topic,
            user_text=heard,
            reply_text=reply,
        )
    )

    t_tts0 = time.perf_counter()
    tts_first_ms: int | None = None
    try:
        async for mp3 in tts.stream_sentences(reply):
            if tts_first_ms is None:
                tts_first_ms = int((time.perf_counter() - t_tts0) * 1000)
            await send_bytes(mp3)
    except Exception as exc:
        log.warning("tts_stream_failed", error=str(exc))
        await send_json(
            {
                "type": "error",
                "detail": "Reply text is ready, but speech playback failed. Use Hear this.",
            }
        )

    analysis: AnalysisResult | None
    try:
        analysis = await analysis_task
    except Exception as exc:
        log.warning("analysis_failed", error=str(exc))
        analysis = None

    if analysis is not None:
        user_row = db.get(m.Message, user_id)
        asst_row = db.get(m.Message, assistant_id)
        corr = None
        if user_row is not None and analysis.translation_en:
            user_row.translation = analysis.translation_en
        if asst_row is not None and analysis.reply_translation_en:
            asst_row.translation = analysis.reply_translation_en
        if user_row is not None and analysis.correction is not None:
            corr = analysis.correction
            db.add(
                m.Correction(
                    message_id=user_id,
                    original=heard,
                    better=analysis.correction.better,
                    reason=analysis.correction.reason,
                )
            )
        db.commit()
        await send_json(
            {
                "type": "analysis",
                "user_message_id": user_id,
                "assistant_message_id": assistant_id,
                "analysis": analysis.model_dump(),
                "user_message": _message_dict(user_row, corr) if user_row else None,
                "assistant_message": _message_dict(asst_row, None) if asst_row else None,
            }
        )

    total_ms = int((time.perf_counter() - t0) * 1000)
    timing: dict[str, object] = {
        "stt_ms": stt_ms,
        "llm_first_token_ms": llm_first_ms,
        "tts_first_byte_ms": tts_first_ms,
        "total_ms": total_ms,
        "session_id": session_id,
        "stt_source": "browser_hint" if hint and heard == hint else "whisper",
    }
    timings_sink.append(timing)
    if len(timings_sink) > 50:
        del timings_sink[:-50]
    log.info("voice_turn_timing", **timing)
    await send_json({"type": "turn.end"})
