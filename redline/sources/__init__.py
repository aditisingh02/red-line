"""Payload sources. Static is always available; live fetchers degrade gracefully."""
from __future__ import annotations

import logging

from ..models import Payload
from .garak import GarakSource
from .huggingface import HuggingFaceSource
from .mitre import MitreSource
from .nvd import NvdSource
from .owasp import OwaspSource
from .static import StaticSource

log = logging.getLogger("redline.sources")

LIVE_SOURCES = [MitreSource, OwaspSource, HuggingFaceSource, GarakSource, NvdSource]


async def collect_payloads(categories: list[str], use_live: bool = True) -> list[Payload]:
    """Aggregate payloads from all sources. Static always runs; live is best-effort."""
    out: list[Payload] = list(StaticSource().fetch(categories))
    if use_live:
        for cls in LIVE_SOURCES:
            try:
                src = cls()
                got = await src.fetch_async(categories)
                out.extend(got)
                log.info("source %s contributed %d payloads", cls.__name__, len(got))
            except Exception as e:  # noqa: BLE001 — never let a source crash the scan
                log.warning("source %s failed, skipping: %s", cls.__name__, e)
    return out


__all__ = ["collect_payloads", "StaticSource"]
