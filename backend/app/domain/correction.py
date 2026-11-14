"""Correction card model."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CorrectionOut(BaseModel):
    better: str
    reason: str


class AnalysisResult(BaseModel):
    translation_en: str = ""
    reply_translation_en: str = ""
    correction: CorrectionOut | None = None
    goal_progress: float = Field(default=0.0, ge=0.0, le=1.0)
    goal_done: bool = False
    suggested_words: list[str] = Field(default_factory=list, max_length=3)
