"""Target adapters."""
from __future__ import annotations

from .anthropic import AnthropicAdapter
from .base import TargetAdapter
from .http import HTTPAdapter
from .mock import MockAdapter
from .openai import OpenAIAdapter


def make_adapter(name: str, target_url: str, auth_headers: dict[str, str] | None = None) -> TargetAdapter:
    auth_headers = auth_headers or {}
    name = (name or "http").lower()
    if name == "mock":
        return MockAdapter()
    if name == "openai":
        return OpenAIAdapter(target_url, auth_headers)
    if name == "anthropic":
        return AnthropicAdapter(target_url, auth_headers)
    return HTTPAdapter(target_url, auth_headers)


__all__ = [
    "TargetAdapter",
    "HTTPAdapter",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "MockAdapter",
    "make_adapter",
]
