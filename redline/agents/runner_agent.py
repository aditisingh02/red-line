"""Runner Agent — executes payloads against the target with retries and timeout.

Crash-prevention guarantees:
- every execution wrapped in try/except (one bad payload never aborts the suite)
- hard per-request timeout (settings.redline_request_timeout)
- exponential backoff 1s -> 2s -> 4s on 429/5xx, max settings.redline_max_retries
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator

import httpx

from ..adapters.base import TargetAdapter
from ..config import settings
from ..models import Payload

log = logging.getLogger("redline.runner_agent")


class RunResult:
    def __init__(self, payload: Payload, response: str, status: str, elapsed_ms: int,
                 error: str | None = None) -> None:
        self.payload = payload
        self.response = response
        self.status = status  # "ok" | "error"
        self.elapsed_ms = elapsed_ms
        self.error = error


class RunnerAgent:
    def __init__(self, adapter: TargetAdapter) -> None:
        self.adapter = adapter

    async def health_check(self) -> bool:
        try:
            return await self.adapter.health_check()
        except Exception as e:  # noqa: BLE001
            log.warning("health check raised: %s", e)
            return False

    async def run_all(self, payloads: list[Payload]) -> AsyncIterator[tuple[RunResult, dict]]:
        """Yield (RunResult, sse_event) for each payload as it completes."""
        total = len(payloads)
        for idx, p in enumerate(payloads, 1):
            yield_event = {
                "test_id": p.id,
                "category": p.category,
                "status": "running",
                "elapsed_ms": 0,
                "index": idx,
                "total": total,
            }
            result = await self._run_one(p)
            ev = {
                "test_id": p.id,
                "category": p.category,
                "status": "error" if result.status == "error" else "done",
                "elapsed_ms": result.elapsed_ms,
                "index": idx,
                "total": total,
            }
            yield result, ev

    async def _run_one(self, p: Payload) -> RunResult:
        start = time.perf_counter()
        delay = 1.0
        last_err = "unknown error"
        for attempt in range(settings.redline_max_retries + 1):
            try:
                resp = await asyncio.wait_for(
                    self.adapter.send_prompt(p.payload),
                    timeout=settings.redline_request_timeout,
                )
                elapsed = int((time.perf_counter() - start) * 1000)
                return RunResult(p, resp or "", "ok", elapsed)
            except asyncio.TimeoutError:
                last_err = f"timeout after {settings.redline_request_timeout}s"
                break  # timeout is terminal — do not retry a hung target
            except httpx.HTTPStatusError as e:
                last_err = f"http {e.response.status_code}"
                if e.response.status_code in (429,) or e.response.status_code >= 500:
                    if attempt < settings.redline_max_retries:
                        await asyncio.sleep(delay)
                        delay *= 2
                        continue
                break
            except Exception as e:  # noqa: BLE001 — never crash the suite
                last_err = f"{type(e).__name__}: {e}"
                break
        elapsed = int((time.perf_counter() - start) * 1000)
        log.warning("payload %s failed: %s", p.id, last_err)
        return RunResult(p, "", "error", elapsed, error=last_err)
