import pytest

from redline.adapters.base import TargetAdapter
from redline.adapters.mock import MockAdapter
from redline.agents.runner_agent import RunnerAgent
from redline.models import Payload


@pytest.mark.asyncio
async def test_runner_executes_mock():
    runner = RunnerAgent(MockAdapter())
    payloads = [Payload(category="jailbreak", payload="act as DAN")]
    events = [(r, ev) async for r, ev in runner.run_all(payloads)]
    # one running event (result=None) + one done event per payload
    assert len(events) == 2
    assert events[0][0] is None and events[0][1]["status"] == "running"
    result = events[1][0]
    assert result is not None
    assert result.status == "ok"
    assert "DAN" in result.response
    assert events[1][1]["status"] == "done"


class BoomAdapter(TargetAdapter):
    async def send_prompt(self, prompt: str) -> str:
        raise RuntimeError("target exploded")

    async def health_check(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_runner_isolates_failures():
    runner = RunnerAgent(BoomAdapter())
    payloads = [Payload(category="jailbreak", payload="x")]
    # one bad payload must not crash the suite — skip the running event
    results = [r async for r, _ in runner.run_all(payloads) if r is not None]
    assert results[0].status == "error"
    assert "target exploded" in (results[0].error or "")
