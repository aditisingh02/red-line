"""OpenAI-compatible chat-completions adapter."""
from __future__ import annotations

import httpx

from ..config import settings
from .base import TargetAdapter


class OpenAIAdapter(TargetAdapter):
    def __init__(self, target_url: str, auth_headers: dict[str, str] | None = None) -> None:
        # target_url is the chat completions endpoint or a base; normalize.
        self.target_url = target_url.rstrip("/")
        if not self.target_url.endswith("/chat/completions"):
            self.target_url += "/chat/completions"
        self.headers = {"Content-Type": "application/json", **(auth_headers or {})}
        self.model = (auth_headers or {}).pop("X-Model", "gpt-3.5-turbo") if auth_headers else "gpt-3.5-turbo"

    async def send_prompt(self, prompt: str) -> str:
        body = {"model": self.model, "messages": [{"role": "user", "content": prompt}]}
        async with httpx.AsyncClient(timeout=settings.redline_request_timeout) as client:
            r = await client.post(self.target_url, json=body, headers=self.headers)
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

    async def health_check(self) -> bool:
        try:
            await self.send_prompt("ping")
            return True
        except (httpx.HTTPError, KeyError, IndexError):
            return False
