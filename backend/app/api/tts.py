"""On-demand TTS for word / sentence replay (same Edge voice as chat)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["tts"])


class SpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=500)
    rate: str = "+0%"


@router.post("/tts")
async def speak(body: SpeakRequest, request: Request) -> Response:
    state = request.app.state.container
    tts = getattr(state, "tts", None)
    if tts is None:
        raise HTTPException(status_code=503, detail="TTS not ready")
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty text")
    try:
        data = await tts.synthesize(text, rate=body.rate)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"TTS failed: {exc}") from exc
    if not data:
        raise HTTPException(status_code=502, detail="TTS returned empty audio")
    return Response(
        content=data,
        media_type="audio/mpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )
