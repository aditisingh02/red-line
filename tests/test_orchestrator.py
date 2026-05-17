import pytest

from redline.models import ScanConfig
from redline.orchestrator import Orchestrator
from redline.report import build_report
from redline.storage import Storage


@pytest.mark.asyncio
async def test_full_mock_scan_produces_findings(tmp_path):
    storage = Storage(tmp_path / "t.db")
    orch = Orchestrator(storage)
    cfg = ScanConfig(mock=True, use_live_sources=False,
                     categories=["prompt_injection", "data_exfiltration"],
                     max_tests=8)
    events = [ev async for ev in orch.scan(cfg)]
    kinds = {e["event"] for e in events}
    assert {"scan_start", "payloads_ready", "scan_complete"} <= kinds

    complete = [e for e in events if e["event"] == "scan_complete"][0]
    sid = complete["scan_id"]
    report = build_report(storage, sid)
    assert report["summary"]["tests_run"] > 0
    # mock target is deliberately vulnerable -> at least one critical/fail
    assert report["summary"]["failed"] >= 1
