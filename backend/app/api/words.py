"""Saved words routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.adapters.persistence import models as m
from app.api.deps import get_db
from app.api.schemas import SavedWordOut, SaveWordRequest
from app.application import chat as chat_uc

router = APIRouter(prefix="/api/words", tags=["words"])


@router.get("", response_model=list[SavedWordOut])
def list_words(
    q: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[SavedWordOut]:
    query = db.query(m.SavedWord).order_by(m.SavedWord.created_at.desc())
    if q:
        like = f"%{q}%"
        query = query.filter((m.SavedWord.word.like(like)) | (m.SavedWord.definition.like(like)))
    rows = query.limit(200).all()
    return [
        SavedWordOut(
            id=r.id,
            word=r.word,
            pinyin=r.pinyin,
            definition=r.definition,
            hsk_level=r.hsk_level,
            context_sentence=r.context_sentence,
            created_at=r.created_at.isoformat() if r.created_at else None,
        )
        for r in rows
    ]


@router.post("", response_model=SavedWordOut)
def save_word(body: SaveWordRequest, db: Session = Depends(get_db)) -> SavedWordOut:
    row = chat_uc.save_word(
        db,
        word=body.word.strip(),
        pinyin=body.pinyin,
        definition=body.definition,
        hsk_level=body.hsk_level,
        context_sentence=body.context_sentence,
    )
    return SavedWordOut(
        id=row.id,
        word=row.word,
        pinyin=row.pinyin,
        definition=row.definition,
        hsk_level=row.hsk_level,
        context_sentence=row.context_sentence,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.delete("/{word_id}")
def delete_word(word_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    row = db.get(m.SavedWord, word_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Word not found")
    db.delete(row)
    return {"status": "deleted"}
