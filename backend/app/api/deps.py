"""FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.application.chat import ChatServices
from app.container import AppState


def get_state(request: Request) -> AppState:
    state = request.app.state.container
    if not isinstance(state, AppState):
        raise HTTPException(status_code=500, detail="App not initialised")
    return state


def get_db(state: AppState = Depends(get_state)) -> Generator[Session, None, None]:
    session = state.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_chat_services(state: AppState = Depends(get_state)) -> ChatServices:
    if state.chat_services is None:
        raise HTTPException(status_code=503, detail="Chat services not ready")
    return state.chat_services
