"""Base class for live payload sources with on-disk caching."""
from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import CACHE_DIR
from ..models import Payload

CACHE_TTL = 24 * 3600  # 1 day


class LiveSource:
    name = "live"

    def _cache_path(self) -> Path:
        return CACHE_DIR / f"{self.name}.json"

    def _read_cache(self) -> list[Payload] | None:
        p = self._cache_path()
        if not p.exists() or (time.time() - p.stat().st_mtime) > CACHE_TTL:
            return None
        try:
            raw = json.loads(p.read_text())
            return [Payload(**d) for d in raw]
        except (ValueError, TypeError):
            return None

    def _write_cache(self, payloads: list[Payload]) -> None:
        try:
            self._cache_path().write_text(
                json.dumps([p.model_dump() for p in payloads], default=str)
            )
        except OSError:
            pass

    async def fetch_async(self, categories: list[str]) -> list[Payload]:
        cached = self._read_cache()
        if cached is not None:
            return self._filter(cached, categories)
        payloads = await self._do_fetch()
        if payloads:
            self._write_cache(payloads)
        return self._filter(payloads, categories)

    async def _do_fetch(self) -> list[Payload]:  # pragma: no cover - overridden
        return []

    @staticmethod
    def _filter(payloads: list[Payload], categories: list[str]) -> list[Payload]:
        if not categories:
            return payloads
        return [p for p in payloads if p.category in categories]
