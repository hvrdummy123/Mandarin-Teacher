"""Topics and level metadata."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.api.schemas import LevelInfoOut, TopicOut
from app.domain.level import level_for_tier, rules_for_level, tier_for_level
from app.domain.topics import get_topic, load_topics

router = APIRouter(prefix="/api", tags=["meta"])


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
