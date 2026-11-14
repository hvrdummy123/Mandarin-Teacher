"""Topics and level metadata."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.schemas import EnrichTextOut, EnrichTextRequest, LevelInfoOut, TopicOut
from app.domain.level import level_for_tier, rules_for_level, tier_for_level
from app.domain.topics import get_topic, load_topics

router = APIRouter(prefix="/api", tags=["meta"])


def _rough_translation(tokens: list[dict[str, object]]) -> str:
    """Dictionary gloss join for live display (not a full sentence translation)."""
    bits: list[str] = []
    for tok in tokens:
        surface = str(tok.get("surface") or "")
        defs = tok.get("definitions")
        if isinstance(defs, list) and defs and isinstance(defs[0], str):
            # CEDICT defs often "surname / hello / ..." — take first sense.
            sense = defs[0].split("/")[0].strip()
            if sense:
                bits.append(sense)
                continue
        if surface.strip():
            bits.append(surface)
    return " ".join(bits)


@router.get("/topics", response_model=list[TopicOut])
def list_topics() -> list[TopicOut]:
    return [
        TopicOut(
            id=t.id,
            title_en=t.title_en,
            title_zh=t.title_zh,
            ai_role=t.ai_role,
            scenario=t.scenario,
            user_goal=t.user_goal,
            keywords=list(t.keywords),
            min_level=t.min_level,
        )
        for t in load_topics()
    ]


@router.get("/topics/{topic_id}", response_model=TopicOut)
def topic_detail(topic_id: str) -> TopicOut:
    t = get_topic(topic_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return TopicOut(
        id=t.id,
        title_en=t.title_en,
        title_zh=t.title_zh,
        ai_role=t.ai_role,
        scenario=t.scenario,
        user_goal=t.user_goal,
        keywords=list(t.keywords),
        min_level=t.min_level,
    )


@router.get("/levels/{level}", response_model=LevelInfoOut)
def level_info(level: int) -> LevelInfoOut:
    if level < 1 or level > 100:
        raise HTTPException(status_code=400, detail="Level must be 1–100")
    rules = rules_for_level(level)
    return LevelInfoOut(
        level=rules.level,
        tier=tier_for_level(level),
        vocab_size=rules.vocab_size,
        max_sentence_chars=rules.max_sentence_chars,
        hsk_band=rules.hsk_band,
        speech_rate=rules.speech_rate,
    )


@router.get("/tiers/{tier}/level")
def tier_to_level(tier: int) -> dict[str, int]:
    if tier < 1 or tier > 10:
        raise HTTPException(status_code=400, detail="Tier must be 1–10")
    return {"tier": tier, "level": level_for_tier(tier)}


@router.get("/levels")
def levels_query(tier: int | None = Query(default=None)) -> dict[str, int | LevelInfoOut]:
    if tier is not None:
        level = level_for_tier(tier)
        rules = rules_for_level(level)
        return {
            "tier": tier,
            "level": level,
            "info": LevelInfoOut(
                level=rules.level,
                tier=tier_for_level(level),
                vocab_size=rules.vocab_size,
                max_sentence_chars=rules.max_sentence_chars,
                hsk_band=rules.hsk_band,
                speech_rate=rules.speech_rate,
            ),
        }
    return {"min": 1, "max": 100}


@router.post("/enrich", response_model=EnrichTextOut)
def enrich_text(body: EnrichTextRequest, request: Request) -> EnrichTextOut:
    """Fast local enrichment for live speech draft (hanzi → pinyin + rough English).

    When topic_id is set, optionally repairs likely STT mix-ups (借口→家, 名词→名字).
    """
    from app.application.transcript_repair import repair_transcript

    container = request.app.state.container
    services = getattr(container, "chat_services", None)
    if services is None:
        raise HTTPException(status_code=503, detail="Dictionary / analyzer not ready")

    original = body.text
    text = body.text
    repaired = False
    repair_note = ""
    if body.repair and body.topic_id:
        result = repair_transcript(body.text, topic_id=body.topic_id)
        text = result.text
        repaired = result.changed
        repair_note = result.note

    tokens = services.analyzer.tokens_as_dicts(text)
    pinyin_line = " ".join(
        str(t.get("pinyin") or t.get("surface") or "") for t in tokens if t.get("surface")
    ).strip()
    return EnrichTextOut(
        text=text,
        tokens=tokens,
        translation_en=_rough_translation(tokens),
        pinyin_line=pinyin_line,
        original_text=original if repaired else None,
        repaired=repaired,
        repair_note=repair_note,
    )
