"""Voice WebSocket handler."""

from __future__ import annotations

import contextlib
import json
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.adapters.stt.vad import FrameVAD
from app.application.voice_turn import run_voice_turn
from app.container import AppState
from app.logging import get_logger

log = get_logger(__name__)
router = APIRouter()

SendJson = Callable[[dict[str, object]], Awaitable[None]]
SendBytes = Callable[[bytes], Awaitable[None]]


@router.websocket("/ws/voice")
async def voice_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    state: AppState = websocket.app.state.container
    session_id: int | None = None
    pcm_buf = bytearray()
    vad = FrameVAD()
    turn_active = False
    auto_ended = False
    # Tap-to-talk waits for explicit turn.end; VAD auto-end only in hands-free.
    hands_free = False

    async def send_json(payload: dict[str, object]) -> None:
        await websocket.send_text(json.dumps(payload, ensure_ascii=False))

    async def send_bytes(data: bytes) -> None:
        await websocket.send_bytes(data)

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            if "text" in message and message["text"] is not None:
                data = json.loads(message["text"])
                typ = data.get("type")
                if typ == "session.start":
                    session_id = int(data["session_id"])
                elif typ == "turn.start":
                    pcm_buf.clear()
                    vad.reset()
                    turn_active = True
                    auto_ended = False
                    hands_free = bool(data.get("hands_free", False))
                elif typ == "turn.end" and turn_active:
                    turn_active = False
                    heard_hint = data.get("heard_hint")
                    hint = heard_hint if isinstance(heard_hint, str) else None
                    await _finish_turn(
                        state,
                        session_id,
                        bytes(pcm_buf),
                        send_json,
                        send_bytes,
                        heard_hint=hint,
                    )
                    pcm_buf.clear()
            elif "bytes" in message and message["bytes"] is not None and turn_active:
                frame = message["bytes"]
                pcm_buf.extend(frame)
                max_bytes = 16000 * 2 * 60
                if len(pcm_buf) > max_bytes:
                    pcm_buf[:] = pcm_buf[-max_bytes:]
                if hands_free and not auto_ended and vad.accept(frame):
                    auto_ended = True
                    turn_active = False
                    await send_json({"type": "vad.end"})
                    await _finish_turn(
                        state,
                        session_id,
                        bytes(pcm_buf),
                        send_json,
                        send_bytes,
                        heard_hint=None,
                    )
                    pcm_buf.clear()
    except WebSocketDisconnect:
        log.info("ws_disconnected", session_id=session_id)
    except Exception as exc:
        log.warning("ws_error", error=str(exc))
        with contextlib.suppress(Exception):
            await send_json({"type": "error", "detail": str(exc)})


async def _finish_turn(
    state: AppState,
    session_id: int | None,
    pcm: bytes,
    send_json: SendJson,
    send_bytes: SendBytes,
    *,
    heard_hint: str | None = None,
) -> None:
    if session_id is None:
        await send_json({"type": "error", "detail": "No session.start yet"})
        return
    if state.chat_services is None or state.stt is None or state.tts is None:
        await send_json({"type": "error", "detail": "Voice services not ready"})
        return
    db = state.session_factory()
    try:
        audio_dir = Path(state.settings.data_dir) / "audio" / str(session_id)
        await run_voice_turn(
            db,
            state.chat_services,
            session_id=session_id,
            pcm=pcm,
            stt=state.stt,
            tts=state.tts,
            audio_dir=audio_dir,
            send_json=send_json,
            send_bytes=send_bytes,
            timings_sink=state.timings,
            heard_hint=heard_hint,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        await send_json({"type": "error", "detail": str(exc)})
    finally:
        db.close()
