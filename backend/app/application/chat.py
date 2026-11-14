"""Text chat use cases: start session, send message, analyse."""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.adapters.llm.fallback import AllProvidersFailed, FallbackChain
from app.adapters.persistence import models as m
from app.application.text_analyzer import TextAnalyzer
from app.domain.correction import AnalysisResult
from app.domain.level import enforce_level_on_reply, rules_for_level
from app.domain.topics import Topic, get_topic
from app.logging import get_logger
from app.prompts.loader import render

log = get_logger(__name__)


@dataclass
class ChatServices:
    llm: FallbackChain
    analyzer: TextAnalyzer
    ranked_vocab: list[str]
    out_of_vocab_threshold: float = 0.12

    def allowed_for_level(self, level: int) -> set[str]:
        from app.domain.level import rules_for_level

        n = rules_for_level(level).vocab_size
        if self.ranked_vocab:
            return set(self.ranked_vocab[:n])
        return set()

    def hint_for_level(self, level: int) -> list[str]:
        from app.domain.level import allowed_vocab_sample

        return allowed_vocab_sample(self.ranked_vocab, level)


def create_session(
    db: Session,
    *,
    mode: str = "free",
    topic_id: str | None = None,
    level: int = 1,
) -> m.Session:
    level = max(1, min(100, level))
    row = m.Session(mode=mode, topic_id=topic_id, level=level)
    db.add(row)
    db.flush()
    return row


def recent_saved_words(db: Session, limit: int = 8) -> list[str]:
    rows = db.query(m.SavedWord).order_by(m.SavedWord.created_at.desc()).limit(limit).all()
    return [r.word for r in rows]


def _topic_block(topic: Topic | None) -> str:
    if topic is None:
        return "Mode: free chat. Be a friendly conversation partner."
    return (
        f"Topic: {topic.title_en} / {topic.title_zh}.\n"
        f"Your role: {topic.ai_role}.\n"
        f"Scenario: {topic.scenario}.\n"
        f"Learner goal: {topic.user_goal}.\n"
        "Stay in role and nudge toward the goal."
    )


def _build_reply_prompt(
    *,
    level: int,
    topic: Topic | None,
    saved: list[str],
    vocab_hint: list[str],
    forbidden: list[str] | None = None,
) -> str:
    rules = rules_for_level(level)
    forbidden_block = ""
    if forbidden:
        forbidden_block = "Do not use these words (too hard for this level): " + "、".join(
            forbidden
        )
    return render(
        "reply.txt",
        level=level,
        hsk_band=rules.hsk_band,
        max_chars=rules.max_sentence_chars,
        topic_block=_topic_block(topic),
        vocab_hint="、".join(vocab_hint) or "(basic greetings)",
        saved_words="、".join(saved) or "(none yet)",
        forbidden_block=forbidden_block,
    )


async def _parse_analysis(raw: str) -> AnalysisResult:
    try:
        data = json.loads(raw)
        if isinstance(data, dict) and "suggested_words" in data:
            sw = data["suggested_words"]
            if isinstance(sw, list):
                data["suggested_words"] = sw[:3]
        return AnalysisResult.model_validate(data)
    except Exception:
        return AnalysisResult()


async def analyse_turn(
    services: ChatServices,
    *,
    level: int,
    topic: Topic | None,
    user_text: str,
    reply_text: str,
) -> AnalysisResult:
    system = render(
        "analysis.txt",
        level=level,
        topic_title=(topic.title_en if topic else "free chat"),
        user_goal=(topic.user_goal if topic else "practise speaking"),
        user_text=user_text,
        reply_text=reply_text,
    )
    try:
        raw = await services.llm.complete(system=system, user=user_text, json_mode=True)
        result = await _parse_analysis(raw)
        if result.translation_en or result.reply_translation_en:
            return result
        # One repair attempt on empty/malformed payload.
        repair = await services.llm.complete(
            system=system + "\nPrevious output was invalid. Return valid JSON only.",
            user=user_text,
            json_mode=True,
        )
        return await _parse_analysis(repair)
    except AllProvidersFailed:
        return AnalysisResult(
            translation_en="",
            reply_translation_en="",
            correction=None,
        )


async def open_topic_with_ai(
    db: Session,
    services: ChatServices,
    *,
    topic_id: str,
    level: int,
) -> dict[str, object]:
    """Create a topic session with an instant canned opening (no LLM wait)."""
    from app.domain.topics import instant_opening

    topic = get_topic(topic_id)
    if topic is None:
        raise ValueError("topic not found")
    session = create_session(db, mode="topic", topic_id=topic_id, level=level)
    reply, reply_en = instant_opening(topic)
    tokens = services.analyzer.tokens_as_dicts(reply)
    assistant_msg = m.Message(
        session_id=session.id,
        role="assistant",
        text=reply,
        pinyin_json=tokens,
        translation=reply_en,
    )
    db.add(assistant_msg)
    db.flush()
    db.commit()
    return {
        "session": {
            "id": session.id,
            "mode": session.mode,
            "topic_id": session.topic_id,
            "level": session.level,
            "created_at": session.created_at.isoformat() if session.created_at else None,
        },
        "assistant_message": _message_dict(assistant_msg, None),
    }


async def send_text_message(
    db: Session,
    services: ChatServices,
    *,
    session_id: int,
    text: str,
) -> dict[str, object]:
    session = db.get(m.Session, session_id)
    if session is None:
        raise ValueError("session not found")

    topic = get_topic(session.topic_id)
    keywords = set(topic.keywords) if topic else set()
    saved = recent_saved_words(db)
    allowed = services.allowed_for_level(session.level)
    vocab_hint = services.hint_for_level(session.level)
    system = _build_reply_prompt(
        level=session.level,
        topic=topic,
        saved=saved,
        vocab_hint=vocab_hint,
    )

    # Persist the user line first with a rough gloss, then call the LLM — keeps SQLite unlocked.
    user_tokens = services.analyzer.tokens_as_dicts(text)
    interim_bits: list[str] = []
    for tok in user_tokens:
        defs = tok.get("definitions")
        if isinstance(defs, list) and defs and isinstance(defs[0], str):
            interim_bits.append(defs[0].split("/")[0].strip())
        else:
            interim_bits.append(str(tok.get("surface") or ""))
    user_msg = m.Message(
        session_id=session.id,
        role="user",
        text=text,
        pinyin_json=user_tokens,
        translation=" ".join(b for b in interim_bits if b) or None,
    )
    db.add(user_msg)
    db.flush()
    user_id = user_msg.id
    db.commit()

    prior = (
        db.query(m.Message)
        .filter(m.Message.session_id == session_id, m.Message.id != user_id)
        .order_by(m.Message.id.desc())
        .limit(8)
        .all()
    )
    prior.reverse()
    history_lines = [f"{row.role}: {row.text}" for row in prior]
    llm_user = text
    if history_lines:
        llm_user = (
            "Recent conversation (stay in this context):\n"
            + "\n".join(history_lines)
            + f"\n\nLearner just said: {text}"
        )

    try:
        first = await services.llm.complete(system=system, user=llm_user, json_mode=False)
    except AllProvidersFailed as exc:
        raise RuntimeError(
            "AI is rate-limited right now (free-tier 429). Wait ~30–60s and try again."
        ) from exc

    async def _regen(forbidden: list[str]) -> str:
        sys2 = _build_reply_prompt(
            level=session.level,
            topic=topic,
            saved=saved,
            vocab_hint=vocab_hint,
            forbidden=forbidden,
        )
        return await services.llm.complete(system=sys2, user=llm_user, json_mode=False)

    checked = await enforce_level_on_reply(
        _regen,
        first_reply=first,
        allowed=allowed,
        keywords=keywords,
        threshold=services.out_of_vocab_threshold,
    )
    reply = checked.text
    regenerated = checked.regenerated
    out_words = list(checked.out_of_level)
    log.info(
        "level_postcheck",
        session_id=session_id,
        share=checked.share,
        regenerated=regenerated,
        out_of_level=out_words,
    )
    analysis = await analyse_turn(
        services,
        level=session.level,
        topic=topic,
        user_text=text,
        reply_text=reply,
    )

    reply_tokens = services.analyzer.tokens_as_dicts(reply, out_of_level=set(out_words))
    user_row = db.get(m.Message, user_id)
    if user_row is not None and analysis.translation_en:
        user_row.translation = analysis.translation_en
    if user_row is not None and analysis.correction is not None:
        db.add(
            m.Correction(
                message_id=user_id,
                original=text,
                better=analysis.correction.better,
                reason=analysis.correction.reason,
            )
        )

    assistant_msg = m.Message(
        session_id=session_id,
        role="assistant",
        text=reply,
        pinyin_json=reply_tokens,
        translation=analysis.reply_translation_en or None,
    )
    db.add(assistant_msg)
    db.flush()

    return {
        "user_message": _message_dict(user_row or user_msg, analysis.correction),
        "assistant_message": _message_dict(assistant_msg, None),
        "analysis": analysis.model_dump(),
        "level_postcheck": {
            "regenerated": regenerated,
            "out_of_level": out_words,
        },
    }


def _message_dict(msg: m.Message, correction: object | None) -> dict[str, object]:
    corr: dict[str, str] | None = None
    if correction is not None and hasattr(correction, "model_dump"):
        dumped = correction.model_dump()
        corr = dumped if isinstance(dumped, dict) else None
    elif msg.correction is not None:
        corr = {
            "better": msg.correction.better,
            "reason": msg.correction.reason,
        }
    return {
        "id": msg.id,
        "session_id": msg.session_id,
        "role": msg.role,
        "text": msg.text,
        "tokens": msg.pinyin_json,
        "translation": msg.translation,
        "correction": corr,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }


def save_word(
    db: Session,
    *,
    word: str,
    pinyin: str,
    definition: str,
    hsk_level: int | None,
    context_sentence: str | None,
) -> m.SavedWord:
    row = m.SavedWord(
        word=word,
        pinyin=pinyin,
        definition=definition,
        hsk_level=hsk_level,
        context_sentence=context_sentence,
    )
    db.add(row)
    db.flush()
    return row
