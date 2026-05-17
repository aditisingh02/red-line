import pytest

from redline.agents import PayloadAgent
from redline.config import CATEGORIES
from redline.sources import StaticSource


def test_static_source_loads_all_categories():
    payloads = StaticSource().fetch([])
    cats = {p.category for p in payloads}
    assert cats == set(CATEGORIES)
    assert len(payloads) >= 30


def test_static_source_filters_by_category():
    only = StaticSource().fetch(["jailbreak"])
    assert only and all(p.category == "jailbreak" for p in only)


@pytest.mark.asyncio
async def test_payload_agent_dedupes_and_caps():
    agent = PayloadAgent()
    payloads = await agent.generate(["prompt_injection", "jailbreak"],
                                    use_live=False, max_tests=4)
    assert len(payloads) <= 4
    texts = [p.payload for p in payloads]
    assert len(texts) == len(set(texts))
    # round-robin balance keeps both categories represented
    assert {p.category for p in payloads} <= {"prompt_injection", "jailbreak"}
