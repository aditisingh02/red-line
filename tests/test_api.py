"""Integration tests for the new endpoints: /metrics, /api/scan-repo,
/api/github/webhook. The webhook's background scan is stubbed so these
stay offline and deterministic."""
import hashlib
import hmac
import json

from fastapi.testclient import TestClient

import api.main as apimain
from redline.config import settings

client = TestClient(apimain.app)


def test_metrics_endpoint_serves_exposition():
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers["content-type"]


def test_scan_repo_reports_clone_error_gracefully(monkeypatch):
    monkeypatch.setattr(apimain, "scan_repo",
                        lambda url, tok: ([], "fatal: repository not found"))
    r = client.post("/api/scan-repo", json={"repo_url": "https://x/none.git"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "error"
    assert body["error"] == "fatal: repository not found"
    assert body["summary"]["risk_level"].startswith("MINIMAL")


def test_scan_repo_sarif_format(monkeypatch):
    from redline.static_scanner import StaticFinding

    finding = StaticFinding("RL-SEC-001", "Hardcoded key", "critical",
                            "a.py", 3, "k = sk-...", "rotate it")
    monkeypatch.setattr(apimain, "scan_repo", lambda url, tok: ([finding], None))
    r = client.post("/api/scan-repo",
                     json={"repo_url": "https://x/r.git", "format": "sarif"})
    assert r.status_code == 200
    doc = r.json()
    assert doc["version"] == "2.1.0"
    assert doc["runs"][0]["results"][0]["ruleId"] == "RL-SEC-001"


def _sig(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_webhook_rejects_bad_signature(monkeypatch):
    monkeypatch.setattr(settings, "github_webhook_secret", "topsecret")
    r = client.post("/api/github/webhook", content=b"{}",
                     headers={"X-Hub-Signature-256": "sha256=deadbeef",
                              "X-GitHub-Event": "pull_request"})
    assert r.status_code == 401


def test_webhook_ignores_non_pr_event(monkeypatch):
    monkeypatch.setattr(settings, "github_webhook_secret", "")
    r = client.post("/api/github/webhook", content=b"{}",
                     headers={"X-GitHub-Event": "push"})
    assert r.status_code == 202
    assert r.json()["status"] == "ignored"


def test_webhook_ignores_pr_without_clone_url(monkeypatch):
    monkeypatch.setattr(settings, "github_webhook_secret", "")
    payload = json.dumps({"action": "opened", "pull_request": {"number": 1},
                          "repository": {"full_name": "o/r"}}).encode()
    r = client.post("/api/github/webhook", content=payload,
                     headers={"X-GitHub-Event": "pull_request"})
    assert r.status_code == 202
    assert r.json()["status"] == "ignored"


def test_webhook_schedules_scan_on_valid_pr(monkeypatch):
    monkeypatch.setattr(settings, "github_webhook_secret", "")

    captured = {}

    def fake_create_task(coro):
        captured["scheduled"] = True
        coro.close()  # don't run network; avoid "never awaited" warning
        return object()

    monkeypatch.setattr(apimain.asyncio, "create_task", fake_create_task)
    payload = json.dumps({
        "action": "opened",
        "pull_request": {"number": 42, "head": {"sha": "abc"}},
        "repository": {"full_name": "o/r",
                       "clone_url": "https://github.com/o/r.git"},
    }).encode()
    r = client.post("/api/github/webhook", content=payload,
                     headers={"X-GitHub-Event": "pull_request"})
    assert r.status_code == 202
    assert r.json() == {"status": "scanning", "repo": "o/r", "pr": 42}
    assert captured.get("scheduled") is True
