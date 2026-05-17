"""Generate demo/demo_scan.db with a compelling pre-seeded scan (offline, no keys).

Runs a real scan against the MockAdapter so the demo DB always has findings.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from redline.models import ScanConfig
from redline.orchestrator import Orchestrator
from redline.storage import Storage

DB_PATH = Path(__file__).resolve().parent / "demo_scan.db"


def main() -> str:
    if DB_PATH.exists():
        DB_PATH.unlink()
    storage = Storage(DB_PATH)
    orch = Orchestrator(storage)
    cfg = ScanConfig(mock=True, use_live_sources=False, categories=[])

    async def _run() -> str:
        sid = ""
        async for ev in orch.scan(cfg):
            if ev.get("event") == "scan_start":
                sid = ev["scan_id"]
        return sid

    sid = asyncio.run(_run())
    print(f"demo scan id: {sid}")
    return sid


if __name__ == "__main__":
    main()
