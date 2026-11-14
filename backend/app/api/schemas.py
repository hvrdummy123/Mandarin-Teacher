"""REST request/response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    mode: str = "free"
    topic_id: str | None = None
    level: int = Field(default=1, ge=1, le=100)


class SessionOut(BaseModel):
    id: int
    mode: str
    topic_id: str | None
    level: int
    created_at: str | None = None


class SendMessageRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class SaveWordRequest(BaseModel):
    word: str
    pinyin: str = ""
    definition: str = ""
    hsk_level: int | None = None
    context_sentence: str | None = None


class SavedWordOut(BaseModel):
    id: int
    word: str
    pinyin: str
    definition: str
    hsk_level: int | None
    context_sentence: str | None
    created_at: str | None = None


class TopicOut(BaseModel):
    id: str
    title_en: str
    title_zh: str
    ai_role: str
    scenario: str
    user_goal: str
    keywords: list[str]
    min_level: int


class LevelInfoOut(BaseModel):
    level: int
    tier: int
    vocab_size: int
    max_sentence_chars: int
    hsk_band: int
    speech_rate: float


class MessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    text: str
    tokens: Any = None
    translation: str | None = None
    correction: dict[str, str] | None = None
    created_at: str | None = None


class ChatTurnOut(BaseModel):
    user_message: MessageOut
    assistant_message: MessageOut
    analysis: dict[str, Any]
    level_postcheck: dict[str, Any]


class OpenTopicRequest(BaseModel):
    topic_id: str
    level: int = Field(default=10, ge=1, le=100)


class OpenTopicOut(BaseModel):
    session: SessionOut
    assistant_message: MessageOut


class ProgressOut(BaseModel):
    xp_today: int = 0
    daily_goal: int = 100
    streak: int = 0
    level: int = 1
    tier: int = 1
    note: str = "Progress tracking fills in during Phase 3. These are stubs."
