"""SSE helpers for streaming scan progress."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator


async def to_sse(events: AsyncIterator[dict]) -> AsyncIterator[dict]:
    """Adapt orchestrator events into sse-starlette EventSourceResponse dicts."""
    async for ev in events:
        yield {"event": ev.get("event", "message"), "data": json.dumps(ev, default=str)}
