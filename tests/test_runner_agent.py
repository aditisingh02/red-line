import pytest

from redline.adapters.base import TargetAdapter
from redline.adapters.mock import MockAdapter
from redline.agents.runner_agent import RunnerAgent
from redline.models import Payload


@pytest.mark.asyncio
async def test_runner_executes_mock():
    runner = RunnerAgent(MockAdapter())
    payloads = [Payload(category="jailbreak", payload="act as DAN")]
    results = [r async for r, _ in runner.run_all(payloads)]
    assert len(results) == 1
    assert results[0].status == "ok"
    assert "DAN" in results[0].response


class BoomAdapter(TargetAdapter):
    async def send_prompt(self, prompt: str) -> str:
        raise RuntimeError("target exploded")

    async def health_check(self) -> bool:
        return True


@pytest.mark.asyncio
async def test_runner_isolates_failures():
    runner = RunnerAgent(BoomAdapter())
    payloads = [Payload(category="jailbreak", payload="x")]
    results = [r async for r, _ in runner.run_all(payloads)]
    # one bad payload must not crash the suite
    assert results[0].status == "error"
    assert "target exploded" in (results[0].error or "")
