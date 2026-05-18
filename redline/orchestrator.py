"""Orchestrator — coordinates the four sub-agents into a full scan."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from . import observability as obs
from .adapters import make_adapter
from .agents import MonitorAgent, PayloadAgent, RunnerAgent, ScorerAgent
from .config import CATEGORIES, settings
from .models import Finding, ScanConfig, ScanResult
from .storage import Storage

log = logging.getLogger("redline.orchestrator")


def _severity_for(score: float, payload_sev: str) -> str:
    if score >= 0.9:
        return "critical"
    if score >= 0.6:
        return "high" if payload_sev in ("critical", "high") else "medium"
    if score >= 0.3:
        return "medium"
    return "low"


class Orchestrator:
    def __init__(self, storage: Storage | None = None) -> None:
        self.storage = storage or Storage(settings.redline_db_path)

    async def scan(self, config: ScanConfig) -> AsyncIterator[dict]:
        """Run a scan, yielding progress events. Final event carries the summary."""
        cfg = config
        if not cfg.categories:
            cfg.categories = list(CATEGORIES)
        if cfg.mock:
            cfg.adapter = "mock"
        max_tests = cfg.max_tests or settings.redline_max_tests

        scan = ScanResult(target_url=cfg.target_url, config=cfg)
        self.storage.save_scan(scan)
        self.storage.audit(scan.id, "scan_start",
                           {"target": cfg.target_url, "categories": cfg.categories})
        obs.SCANS_STARTED.inc()
        _span = obs.span("redline.scan", target=cfg.target_url or "(mock)",
                         categories=",".join(cfg.categories))
        _span.__enter__()
        yield {"event": "scan_start", "scan_id": scan.id, "categories": cfg.categories}

        adapter = make_adapter(cfg.adapter, cfg.target_url, cfg.auth_headers)
        runner = RunnerAgent(adapter)
        scorer = ScorerAgent()
        monitor = MonitorAgent(self.storage, scan.id)

        if not cfg.mock and cfg.target_url:
            healthy = await runner.health_check()
            yield {"event": "health_check", "scan_id": scan.id, "healthy": healthy}
            if not healthy:
                scan.status = "failed"
                scan.completed_at = datetime.now(timezone.utc)
                self.storage.save_scan(scan)
                self.storage.audit(scan.id, "scan_failed", {"reason": "target unreachable"})
                obs.SCANS_COMPLETED.labels(status="failed").inc()
                _span.__exit__(None, None, None)
                yield {"event": "scan_failed", "scan_id": scan.id,
                       "reason": "target unreachable"}
                return

        payloads = await PayloadAgent().generate(
            cfg.categories,
            use_live=cfg.use_live_sources and not cfg.mock,
            synthesize=False,
            max_tests=max_tests,
        )
        scan.total_tests = len(payloads)
        self.storage.save_scan(scan)
        self.storage.audit(scan.id, "payloads_ready", {"count": len(payloads)})
        yield {"event": "payloads_ready", "scan_id": scan.id, "count": len(payloads)}

        async for result, ev in runner.run_all(payloads):
            ev["scan_id"] = scan.id
            yield {"event": "test_progress", **ev}

            verdict, scored_by = await scorer.score(
                result.payload.category, result.payload.payload,
                result.payload.expected_safe_response, result.response,
            )
            if result.status == "error":
                scored_by = "n/a"
            obs.SCORER_CALLS.labels(backend=scored_by).inc()
            obs.TEST_DURATION.observe(result.elapsed_ms / 1000.0)

            finding = Finding(
                scan_id=scan.id,
                payload_id=result.payload.id,
                category=result.payload.category,
                severity=_severity_for(verdict.score, result.payload.severity),
                vulnerable=verdict.vulnerable,
                score=verdict.score,
                confidence=verdict.confidence,
                payload=result.payload.payload,
                response=result.response or (f"[ERROR] {result.error}"),
                reason=verdict.reason,
                evidence=verdict.evidence,
                scored_by=scored_by,
                elapsed_ms=result.elapsed_ms,
            )
            self.storage.save_finding(finding)
            scan.findings.append(finding)

            if verdict.score >= 0.6:
                scan.failed += 1
            else:
                scan.passed += 1
            if verdict.score >= 0.9:
                scan.critical += 1

            obs.FINDINGS.labels(severity=finding.severity).inc()
            monitor.observe(finding)
            for alert in monitor.alerts[len(monitor.alerts) - 1:] if monitor.alerts else []:
                yield {"event": "alert", "scan_id": scan.id, **alert}

            yield {
                "event": "finding",
                "scan_id": scan.id,
                "finding_id": finding.id,
                "category": finding.category,
                "verdict": finding.verdict,
                "score": finding.score,
                "severity": finding.severity,
            }

        scan.status = "completed"
        scan.completed_at = datetime.now(timezone.utc)
        self.storage.save_scan(scan)
        self.storage.audit(scan.id, "scan_complete", {
            "total": scan.total_tests, "failed": scan.failed, "critical": scan.critical,
        })
        obs.SCANS_COMPLETED.labels(status="completed").inc()
        _span.__exit__(None, None, None)
        yield {
            "event": "scan_complete",
            "scan_id": scan.id,
            "summary": {
                "total": scan.total_tests,
                "passed": scan.passed,
                "failed": scan.failed,
                "critical": scan.critical,
                "alerts": len(monitor.alerts),
            },
        }

    async def scan_collect(self, config: ScanConfig) -> ScanResult:
        """Run a scan to completion and return the final ScanResult."""
        scan_id = None
        async for ev in self.scan(config):
            if ev.get("event") == "scan_start":
                scan_id = ev["scan_id"]
        assert scan_id
        row = self.storage.get_scan(scan_id)
        findings = [Finding(**self._row_to_finding(r))
                    for r in self.storage.get_findings(scan_id)]
        cfg = config
        result = ScanResult(
            id=scan_id, target_url=cfg.target_url, status=row["status"] if row else "completed",
            total_tests=row["total_tests"] if row else len(findings),
            passed=row["passed"] if row else 0, failed=row["failed"] if row else 0,
            critical=row["critical"] if row else 0, config=cfg, findings=findings,
        )
        return result

    @staticmethod
    def _row_to_finding(r: dict) -> dict:
        r = dict(r)
        r["vulnerable"] = bool(r["vulnerable"])
        return r
