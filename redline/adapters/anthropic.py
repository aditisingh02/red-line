"""Anthropic Messages API adapter."""
from __future__ import annotations

import httpx

from ..config import settings
from .base import TargetAdapter


class AnthropicAdapter(TargetAdapter):
    def __init__(self, target_url: str, auth_headers: dict[str, str] | None = None) -> None:
        self.target_url = target_url or settings.anthropic_base_url
        hdr = dict(auth_headers or {})
        self.model = hdr.pop("X-Model", settings.anthropic_model)
        self.headers = {
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            **hdr,
        }

    async def send_prompt(self, prompt: str) -> str:
        body = {
            "model": self.model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=settings.redline_request_timeout) as client:
            r = await client.post(self.target_url, json=body, headers=self.headers)
            r.raise_for_status()
            return r.json()["content"][0]["text"]

    async def health_check(self) -> bool:
        try:
            await self.send_prompt("ping")
            return True
        except (httpx.HTTPError, KeyError, IndexError):
            return False
