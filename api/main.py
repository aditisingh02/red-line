"""FastAPI app exposing the Redline scan API."""
from __future__ import annotations

import asyncio
import json
import time
from collections import deque

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from redline import __version__
from redline import auth
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

# Per-IP sliding window for the unauthed freemium endpoint.
_RATE_WINDOW_SEC = 3600
_RATE_LIMIT = 5
_rate_hits: dict[str, deque[float]] = {}


def _rate_limit_ok(ip: str) -> bool:
    now = time.time()
    bucket = _rate_hits.setdefault(ip, deque())
    while bucket and now - bucket[0] > _RATE_WINDOW_SEC:
        bucket.popleft()
    if len(bucket) >= _RATE_LIMIT:
        return False
    bucket.append(now)
    return True


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
        "auth_enabled": auth.oauth_configured(),
    }


# --- auth ------------------------------------------------------------

def current_user_optional(request: Request) -> auth.User | None:
    return auth.resolve_session(_storage, request.cookies.get(auth.SESSION_COOKIE))


def current_user(request: Request) -> auth.User:
    user = current_user_optional(request)
    if not user:
        raise HTTPException(status_code=401, detail="not authenticated")
    return user


@app.get("/api/auth/github/login")
async def auth_github_login() -> Response:
    if not auth.oauth_configured():
        raise HTTPException(
            status_code=503,
            detail="GitHub OAuth not configured "
                   "(set GITHUB_OAUTH_CLIENT_ID + GITHUB_OAUTH_CLIENT_SECRET)",
        )
    state = auth.new_state_token()
    resp = RedirectResponse(auth.build_authorize_url(state), status_code=307)
    resp.set_cookie(
        auth.STATE_COOKIE, state,
        max_age=600, httponly=True, samesite="lax",
        secure=settings.github_oauth_redirect_uri.startswith("https://"),
    )
    return resp


@app.get("/api/auth/github/callback")
async def auth_github_callback(
    request: Request, code: str = "", state: str = "", error: str = "",
) -> Response:
    if error:
        raise HTTPException(status_code=400, detail=f"github oauth error: {error}")
    expected = request.cookies.get(auth.STATE_COOKIE) or ""
    if not code or not state or state != expected:
        raise HTTPException(status_code=400, detail="invalid oauth state")
    try:
        token = await auth.exchange_code_for_token(code)
        profile = await auth.fetch_github_user(token)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"github exchange failed: {e}")

    user_row = _storage.upsert_user_from_github(
        github_id=profile["github_id"],
        github_login=profile["github_login"],
        name=profile["name"],
        email=profile["email"],
        avatar_url=profile["avatar_url"],
        access_token=token,
    )
    session_token, expires = auth.issue_session(_storage, user_row["id"])
    resp = RedirectResponse(settings.auth_post_login_redirect, status_code=303)
    resp.delete_cookie(auth.STATE_COOKIE)
    resp.set_cookie(
        auth.SESSION_COOKIE, session_token,
        expires=expires.timestamp(), httponly=True, samesite="lax",
        secure=settings.auth_post_login_redirect.startswith("https://"),
        path="/",
    )
    return resp


@app.post("/api/auth/logout")
async def auth_logout(request: Request) -> Response:
    auth.revoke_session(_storage, request.cookies.get(auth.SESSION_COOKIE))
    resp = Response(status_code=204)
    resp.delete_cookie(auth.SESSION_COOKIE, path="/")
    return resp


@app.get("/api/auth/me")
async def auth_me(user: auth.User = Depends(current_user)) -> dict:
    return user.public_dict()


async def _run_scan(
    scan_id_holder: dict, cfg: ScanConfig, user_id: str | None = None,
) -> None:
    buf: list[dict] = []
    async for ev in _orch.scan(cfg, user_id=user_id):
        if ev.get("event") == "scan_start":
            sid = ev["scan_id"]
            scan_id_holder["id"] = sid
            _streams[sid] = buf
        if scan_id_holder.get("id") in _cancelled:
            buf.append({"event": "scan_cancelled", "scan_id": scan_id_holder["id"]})
            break
        buf.append(ev)


@app.post("/api/scans")
async def create_scan(
    req: ScanRequest, request: Request,
) -> dict:
    cfg = ScanConfig(**req.model_dump())
    user = current_user_optional(request)
    holder: dict = {}
    task = asyncio.create_task(_run_scan(holder, cfg, user.id if user else None))
    # wait briefly for the scan_id to be assigned
    for _ in range(50):
        if holder.get("id"):
            break
        await asyncio.sleep(0.05)
    app.state.__dict__.setdefault("tasks", []).append(task)
    return {"scan_id": holder.get("id"), "status": "started"}


@app.get("/api/scans")
async def list_scans(request: Request, limit: int = 50) -> dict:
    """Anonymous → all scans (legacy). Logged-in → only the user's scans."""
    user = current_user_optional(request)
    return {
        "scans": _storage.list_scans(
            limit=limit, user_id=user.id if user else None,
        )
    }


@app.get("/api/me/scans")
async def my_scans(
    user: auth.User = Depends(current_user), limit: int = 50,
) -> dict:
    """Logged-in users' scans only. 401 if not authenticated."""
    return {"scans": _storage.list_scans(limit=limit, user_id=user.id)}


# --- dashboard aggregates ------------------------------------------

def _user_scope(request: Request) -> str | None:
    u = current_user_optional(request)
    return u.id if u else None


@app.get("/api/dashboard/stats")
async def dashboard_stats(request: Request) -> dict:
    """Counts for the overview cards. Scoped to the logged-in user if any."""
    return _storage.aggregate_stats(user_id=_user_scope(request))


@app.get("/api/dashboard/findings")
async def dashboard_findings(
    request: Request,
    limit: int = 50,
    severity: str | None = None,
    category: str | None = None,
) -> dict:
    return {
        "findings": _storage.list_findings(
            user_id=_user_scope(request),
            limit=limit,
            severity=severity,
            category=category,
        )
    }


@app.get("/api/dashboard/repos")
async def dashboard_repos(request: Request) -> dict:
    return {"repos": _storage.list_repos(user_id=_user_scope(request))}


@app.get("/api/dashboard/trend")
async def dashboard_trend(request: Request, days: int = 30) -> dict:
    return {"trend": _storage.scans_over_time(user_id=_user_scope(request), days=days)}


@app.get("/api/scans/{scan_id}/audit")
async def get_scan_audit(scan_id: str) -> dict:
    """Audit timeline for a single scan (used by the dashboard drawer)."""
    if not _storage.get_scan(scan_id):
        raise HTTPException(status_code=404, detail="scan not found")
    return {"events": _storage.get_audit(scan_id)}


@app.get("/api/scans/{scan_id}")
async def get_scan(scan_id: str) -> dict:
    scan = _storage.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="scan not found")
    return {
        "scan": scan,
        "findings": _storage.get_findings(scan_id),
        "summary": build_report(_storage, scan_id)["summary"],
    }


@app.get("/api/scans/{scan_id}/stream")
async def stream_scan(scan_id: str) -> EventSourceResponse:
    async def buffered_events():
        idx = 0
        while True:
            buf = _streams.get(scan_id, [])
            while idx < len(buf):
                ev = buf[idx]
                idx += 1
                yield ev
                if ev.get("event") in ("scan_complete", "scan_failed", "scan_cancelled"):
                    return
            await asyncio.sleep(0.2)

    return EventSourceResponse(to_sse(buffered_events()))


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
async def scan_url(req: UrlRequest, request: Request):
    """Freemium quick scan — capped, no auth, rate-limited per IP."""
    ip = (request.client.host if request.client else "") or "unknown"
    if not _rate_limit_ok(ip):
        return JSONResponse(
            {"error": "rate_limited",
             "detail": f"max {_RATE_LIMIT} freemium scans per hour per IP"},
            status_code=429,
        )
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
    # post_pr_comment uses sync httpx; run off the event loop
    await asyncio.to_thread(
        gh.post_pr_comment, repo, pr_number, body, settings.github_token)


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
        payload = json.loads(raw or b"{}")
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
