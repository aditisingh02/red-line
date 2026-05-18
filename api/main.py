"""FastAPI app exposing the Redline scan API."""
from __future__ import annotations

import asyncio
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from redline import __version__
from redline import observability as obs
from redline.config import settings
from redline.integrations import github as gh
from redline.models import ScanConfig
from redline.orchestrator import Orchestrator
from redline.report import build_report
from redline.static_scanner import build_static_report, scan_repo, to_sarif
from redline.storage import Storage

from .sse import to_sse

app = FastAPI(title="Redline", version=__version__)
_storage = Storage(settings.redline_db_path)
_orch = Orchestrator(_storage)
_started = time.time()

# scan_id -> live event buffer for the SSE stream
_streams: dict[str, list[dict]] = {}
_cancelled: set[str] = set()


class ScanRequest(BaseModel):
    target_url: str = ""
    auth_headers: dict[str, str] = {}
    categories: list[str] = []
    max_tests: int | None = None
    depth: str = "standard"
    adapter: str = "http"
    mock: bool = False
    use_live_sources: bool = True


class UrlRequest(BaseModel):
    url: str


class RepoRequest(BaseModel):
    repo_url: str
    github_token: str = ""
    format: str = "json"  # json | sarif


@app.get("/api/health")
async def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "uptime": round(time.time() - _started, 1),
        "scorer": settings.scorer_backend,
    }


async def _run_scan(scan_id_holder: dict, cfg: ScanConfig) -> None:
    buf: list[dict] = []
    async for ev in _orch.scan(cfg):
        if ev.get("event") == "scan_start":
            sid = ev["scan_id"]
            scan_id_holder["id"] = sid
            _streams[sid] = buf
        if scan_id_holder.get("id") in _cancelled:
            buf.append({"event": "scan_cancelled", "scan_id": scan_id_holder["id"]})
            break
        buf.append(ev)


@app.post("/api/scans")
async def create_scan(req: ScanRequest) -> dict:
    cfg = ScanConfig(**req.model_dump())
    holder: dict = {}
    task = asyncio.create_task(_run_scan(holder, cfg))
    # wait briefly for the scan_id to be assigned
    for _ in range(50):
        if holder.get("id"):
            break
        await asyncio.sleep(0.05)
    app.state.__dict__.setdefault("tasks", []).append(task)
    return {"scan_id": holder.get("id"), "status": "started"}


@app.get("/api/scans/{scan_id}")
async def get_scan(scan_id: str) -> dict:
    scan = _storage.get_scan(scan_id)
    if not scan:
        return {"error": "not found"}
    return {
        "scan": scan,
        "findings": _storage.get_findings(scan_id),
        "summary": build_report(_storage, scan_id)["summary"],
    }


@app.get("/api/scans/{scan_id}/stream")
async def stream_scan(scan_id: str) -> EventSourceResponse:
    async def gen():
        idx = 0
        while True:
            buf = _streams.get(scan_id, [])
            while idx < len(buf):
                ev = buf[idx]
                idx += 1
                yield {"event": ev.get("event", "message"),
                       "data": __import__("json").dumps(ev, default=str)}
                if ev.get("event") in ("scan_complete", "scan_failed", "scan_cancelled"):
                    return
            await asyncio.sleep(0.2)

    return EventSourceResponse(gen())


@app.post("/api/scans/{scan_id}/cancel")
async def cancel_scan(scan_id: str) -> dict:
    _cancelled.add(scan_id)
    return {"status": "cancelled"}


@app.get("/api/scans/{scan_id}/report")
async def get_report(scan_id: str, format: str = "json") -> dict:
    report = build_report(_storage, scan_id)
    if format == "pdf":
        report["_note"] = "PDF export not implemented in v1 (backend build); use JSON."
    return report


@app.post("/api/scan-url")
async def scan_url(req: UrlRequest) -> dict:
    """Freemium quick scan — capped, no auth."""
    cfg = ScanConfig(
        target_url=req.url, adapter="http",
        categories=["prompt_injection", "jailbreak", "data_exfiltration"],
        max_tests=10,
    )
    result = await _orch.scan_collect(cfg)
    return build_report(_storage, result.id)


@app.post("/api/scan-repo")
async def scan_repo_endpoint(req: RepoRequest):
    """Shallow-clone a repo and statically scan it for insecure agent patterns."""
    token = req.github_token or settings.github_token
    findings, error = await asyncio.to_thread(scan_repo, req.repo_url, token)
    if req.format == "sarif":
        return JSONResponse(to_sarif(req.repo_url, findings))
    return build_static_report(req.repo_url, findings, error)


@app.get("/metrics")
async def metrics() -> Response:
    body, content_type = obs.render_metrics()
    return Response(content=body, media_type=content_type)


async def _run_repo_scan(repo: str, clone_url: str, pr_number: int) -> None:
    findings, error = await asyncio.to_thread(
        scan_repo, clone_url, settings.github_token)
    report = build_static_report(clone_url, findings, error)
    body = gh.pr_comment_markdown(report)
    gh.post_pr_comment(repo, pr_number, body, settings.github_token)


@app.post("/api/github/webhook")
async def github_webhook(request: Request) -> JSONResponse:
    """GitHub App webhook: scans PRs and (best-effort) comments findings back."""
    raw = await request.body()
    sig = request.headers.get("X-Hub-Signature-256")
    if not gh.verify_signature(settings.github_webhook_secret, raw, sig):
        return JSONResponse({"error": "invalid signature"}, status_code=401)
    if request.headers.get("X-GitHub-Event") != "pull_request":
        return JSONResponse({"status": "ignored"}, status_code=202)
    try:
        payload = __import__("json").loads(raw or b"{}")
    except ValueError:
        return JSONResponse({"error": "bad payload"}, status_code=400)
    ev = gh.extract_pr_event(payload)
    if not ev or not ev["clone_url"] or not ev["pr_number"]:
        return JSONResponse({"status": "ignored"}, status_code=202)
    task = asyncio.create_task(
        _run_repo_scan(ev["repo"], ev["clone_url"], ev["pr_number"]))
    app.state.__dict__.setdefault("tasks", []).append(task)
    return JSONResponse(
        {"status": "scanning", "repo": ev["repo"], "pr": ev["pr_number"]},
        status_code=202)
