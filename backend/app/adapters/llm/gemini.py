"""Google Gemini free-tier adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx

from app.logging import get_logger

log = get_logger(__name__)


class GeminiAdapter:
    name = "gemini"

    def __init__(
        self,
        api_key: str,
        *,
        reply_model: str,
        analysis_model: str,
        timeout_s: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.reply_model = reply_model
        self.analysis_model = analysis_model
        self.timeout_s = timeout_s

    def _url(self, model: str, stream: bool = False) -> str:
        action = "streamGenerateContent" if stream else "generateContent"
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:{action}?key={self.api_key}"
        )

    async def complete(self, *, system: str, user: str, json_mode: bool = False) -> str:
        model = self.analysis_model if json_mode else self.reply_model
        body: dict[str, object] = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
        }
        if json_mode:
            body["generationConfig"] = {"responseMimeType": "application/json"}
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.post(self._url(model), json=body)
            if resp.status_code in {429} or resp.status_code >= 500:
                resp.raise_for_status()
            if resp.status_code >= 400:
                resp.raise_for_status()
            data = resp.json()
        return _extract_gemini_text(data)

    async def stream(self, *, system: str, user: str) -> AsyncIterator[str]:
        # Gemini streaming is fiddly; for P1 we complete then chunk.
        # Real SSE streaming can land when voice needs first-token latency.
        text = await self.complete(system=system, user=user, json_mode=False)
        for i in range(0, len(text), 8):
            yield text[i : i + 8]


def _extract_gemini_text(data: dict[str, object]) -> str:
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return ""
    first = candidates[0]
    if not isinstance(first, dict):
        return ""
    content = first.get("content")
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if not isinstance(parts, list):
        return ""
    bits: list[str] = []
    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            bits.append(part["text"])
    return "".join(bits)
