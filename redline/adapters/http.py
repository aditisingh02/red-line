"""Generic REST adapter: POST {"prompt": ...} and read a text field back."""
from __future__ import annotations

import httpx

from ..config import settings
from .base import TargetAdapter

_RESPONSE_KEYS = ("response", "output", "text", "message", "answer", "completion", "reply")


def _extract(data: object) -> str:
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        for k in _RESPONSE_KEYS:
            if k in data and isinstance(data[k], str):
                return data[k]
        # OpenAI-ish shapes
        try:
            return data["choices"][0]["message"]["content"]  # type: ignore[index]
        except (KeyError, IndexError, TypeError):
            pass
        return str(data)
    return str(data)


class HTTPAdapter(TargetAdapter):
    def __init__(self, target_url: str, auth_headers: dict[str, str] | None = None) -> None:
        self.target_url = target_url
        self.headers = {"Content-Type": "application/json", **(auth_headers or {})}

    async def send_prompt(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=settings.redline_request_timeout) as client:
            r = await client.post(self.target_url, json={"prompt": prompt}, headers=self.headers)
            r.raise_for_status()
            try:
                return _extract(r.json())
            except ValueError:
                return r.text

    async def health_check(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=settings.redline_request_timeout) as client:
                r = await client.post(
                    self.target_url, json={"prompt": "ping"}, headers=self.headers
                )
                return r.status_code < 500
        except httpx.HTTPError:
            return False
