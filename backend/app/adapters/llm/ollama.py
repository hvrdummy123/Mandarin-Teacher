"""Local Ollama adapter."""

from __future__ import annotations

from collections.abc import AsyncIterator

import httpx


class OllamaAdapter:
    name = "ollama"

    def __init__(
        self,
        base_url: str,
        *,
        reply_model: str,
        analysis_model: str,
        timeout_s: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.reply_model = reply_model
        self.analysis_model = analysis_model
        self.timeout_s = timeout_s

    async def complete(self, *, system: str, user: str, json_mode: bool = False) -> str:
        model = self.analysis_model if json_mode else self.reply_model
        body: dict[str, object] = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            body["format"] = "json"
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=body)
            resp.raise_for_status()
            data = resp.json()
        message = data.get("message") or {}
        content = message.get("content") or ""
        return content if isinstance(content, str) else str(content)

    async def stream(self, *, system: str, user: str) -> AsyncIterator[str]:
        text = await self.complete(system=system, user=user, json_mode=False)
        for i in range(0, len(text), 8):
            yield text[i : i + 8]
