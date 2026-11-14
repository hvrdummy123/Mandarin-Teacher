"""Session and message routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.adapters.persistence import models as m
from app.api.deps import get_chat_services, get_db
from app.api.schemas import (
    ChatTurnOut,
    CreateSessionRequest,
    MessageOut,
    OpenTopicOut,
    OpenTopicRequest,
    SendMessageRequest,
    SessionOut,
)
from app.application import chat as chat_uc
from app.application.chat import ChatServices

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=SessionOut)
def create_session(
    body: CreateSessionRequest,
    db: Session = Depends(get_db),
) -> SessionOut:
    row = chat_uc.create_session(db, mode=body.mode, topic_id=body.topic_id, level=body.level)
    return SessionOut(
        id=row.id,
        mode=row.mode,
        topic_id=row.topic_id,
        level=row.level,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: int, db: Session = Depends(get_db)) -> SessionOut:
    row = db.get(m.Session, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionOut(
        id=row.id,
        mode=row.mode,
        topic_id=row.topic_id,
        level=row.level,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def list_messages(session_id: int, db: Session = Depends(get_db)) -> list[MessageOut]:
    rows = (
        db.query(m.Message)
        .filter(m.Message.session_id == session_id)
        .order_by(m.Message.id.asc())
        .all()
    )
    out: list[MessageOut] = []
    for msg in rows:
        corr = None
        if msg.correction is not None:
            corr = {"better": msg.correction.better, "reason": msg.correction.reason}
        out.append(
            MessageOut(
                id=msg.id,
                session_id=msg.session_id,
                role=msg.role,
                text=msg.text,
                tokens=msg.pinyin_json,
                translation=msg.translation,
                correction=corr,
                created_at=msg.created_at.isoformat() if msg.created_at else None,
            )
        )
    return out


@router.post("/open-topic", response_model=OpenTopicOut)
async def open_topic(
    body: OpenTopicRequest,
    db: Session = Depends(get_db),
    services: ChatServices = Depends(get_chat_services),
) -> OpenTopicOut:
    try:
        result = await chat_uc.open_topic_with_ai(
            db, services, topic_id=body.topic_id, level=body.level
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return OpenTopicOut.model_validate(result)


@router.post("/{session_id}/messages", response_model=ChatTurnOut)
async def send_message(
    session_id: int,
    body: SendMessageRequest,
    db: Session = Depends(get_db),
    services: ChatServices = Depends(get_chat_services),
) -> ChatTurnOut:
    try:
        result = await chat_uc.send_text_message(
            db, services, session_id=session_id, text=body.text.strip()
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return ChatTurnOut.model_validate(result)
