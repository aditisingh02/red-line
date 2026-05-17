"""Hugging Face datasets (HarmBench / AdvBench style) via the public datasets-server.

No `datasets` dependency required: we hit the HF datasets-server REST API. If it
is unreachable or rate-limited, the source simply yields nothing and the scan
falls back to other sources.
"""
from __future__ import annotations

import httpx

from ..config import settings
from ..models import Payload
from .base import LiveSource

# Public harmful-behavior dataset exposed via datasets-server first-rows endpoint.
HF_ROWS_URL = (
    "https://datasets-server.huggingface.co/first-rows"
    "?dataset=walledai/AdvBench&config=default&split=train"
)
_PROMPT_FIELDS = ("prompt", "goal", "behavior", "text", "instruction")


class HuggingFaceSource(LiveSource):
    name = "huggingface"

    async def _do_fetch(self) -> list[Payload]:
        async with httpx.AsyncClient(timeout=settings.redline_request_timeout) as client:
            r = await client.get(HF_ROWS_URL)
            r.raise_for_status()
            data = r.json()
        out: list[Payload] = []
        for row in data.get("rows", [])[:30]:
            rec = row.get("row", {})
            text = next((rec[f] for f in _PROMPT_FIELDS if rec.get(f)), None)
            if not text:
                continue
            out.append(
                Payload(
                    category="jailbreak",
                    subcategory="advbench",
                    payload=str(text),
                    expected_safe_response="Refuses the harmful behavior request.",
                    source="harmbench",
                    severity="high",
                    tags=["huggingface", "advbench"],
                )
            )
        return out
