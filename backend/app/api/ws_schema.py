"""WebSocket control message schema (JSON text frames).

Binary frames: client→server PCM s16le 16kHz mono; server→client MP3.
Generate matching TS with: python scripts/gen_ws_types.py
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SessionStart(BaseModel):
    type: Literal["session.start"] = "session.start"
    session_id: int
    level: int | None = None


class TurnStart(BaseModel):
    type: Literal["turn.start"] = "turn.start"
    hands_free: bool = False


class TurnEnd(BaseModel):
    type: Literal["turn.end"] = "turn.end"


class TranscriptUser(BaseModel):
    type: Literal["transcript.user"] = "transcript.user"
    message: dict[str, Any]


class ReplyDelta(BaseModel):
    type: Literal["reply.delta"] = "reply.delta"
    text: str


class ReplySentence(BaseModel):
    type: Literal["reply.sentence"] = "reply.sentence"
    text: str
    message: dict[str, Any] | None = None


class AnalysisEvent(BaseModel):
    type: Literal["analysis"] = "analysis"
    analysis: dict[str, Any]


class ToneReport(BaseModel):
    type: Literal["tone.report"] = "tone.report"
    report: dict[str, Any] = Field(default_factory=dict)


class XPAwarded(BaseModel):
    type: Literal["xp.awarded"] = "xp.awarded"
    points: int = 0


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    detail: str


class TurnEndAck(BaseModel):
    type: Literal["turn.end"] = "turn.end"
