"""OpenRouter free-model adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx


class OpenRouterAdapter:
    name = "openrouter"

    def __init__(
        self,
        api_key: str,
        *,
        reply_model: str,
        analysis_model: str,
        timeout_s: float = 45.0,
    ) -> None:
        self.api_key = api_key
        self.reply_model = reply_model
        self.analysis_model = analysis_model
        self.timeout_s = timeout_s

    async def complete(self, *, system: str, user: str, json_mode: bool = False) -> str:
        model = self.analysis_model if json_mode else self.reply_model
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://127.0.0.1:5173",
            "X-Title": "duihua",
        }
        body: dict[str, object] = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        content = message.get("content") or ""
        return content if isinstance(content, str) else str(content)

    async def stream(self, *, system: str, user: str) -> AsyncIterator[str]:
        text = await self.complete(system=system, user=user, json_mode=False)
        for i in range(0, len(text), 8):
            yield text[i : i + 8]
