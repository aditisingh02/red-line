"""Garak (NVIDIA LLM probe library) integration — optional import.

If `garak` is installed we pull a few representative probe prompts from its
data files. If not installed, the source contributes nothing (no crash).
"""
from __future__ import annotations

from ..models import Payload
from .base import LiveSource

# garak probe module -> our category
_PROBE_MAP = {
    "dan": ("jailbreak", "DAN-family jailbreak from garak.probes.dan"),
    "promptinject": ("prompt_injection", "Prompt-injection probe from garak.probes.promptinject"),
    "leakreplay": ("data_exfiltration", "Training-data leak probe from garak.probes.leakreplay"),
}


class GarakSource(LiveSource):
    name = "garak"

    async def _do_fetch(self) -> list[Payload]:
        try:
            import garak  # noqa: F401
            import garak.probes  # noqa: F401
        except Exception:
            # Not installed — skip silently; aggregator logs the skip.
            return []

        out: list[Payload] = []
        for probe_name, (cat, desc) in _PROBE_MAP.items():
            try:
                mod = __import__(f"garak.probes.{probe_name}", fromlist=["*"])
            except Exception:
                continue
            prompts: list[str] = []
            for attr in vars(mod).values():
                p = getattr(attr, "prompts", None)
                if isinstance(p, (list, tuple)):
                    prompts.extend(str(x) for x in p[:5])
            for pr in prompts[:5] or [desc]:
                out.append(
                    Payload(
                        category=cat,
                        subcategory=f"garak:{probe_name}",
                        payload=pr,
                        expected_safe_response="Resists the garak probe.",
                        source="garak",
                        severity="high",
                        tags=["garak", probe_name],
                    )
                )
        return out
