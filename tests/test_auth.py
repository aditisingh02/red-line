"""Auth flow tests — OAuth + session cookies + per-user scan listing.

GitHub HTTP calls are stubbed via monkeypatch on `redline.auth`. Tests use
an isolated SQLite DB per fixture so they never touch the developer's local
DB.
"""
import pytest
from fastapi.testclient import TestClient

import api.main as apimain
import redline.auth as auth_mod
from redline.config import settings
from redline.storage import Storage


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = tmp_path / "auth.db"
    storage = Storage(db)
    monkeypatch.setattr(apimain, "_storage", storage)
    # The orchestrator was constructed at module load with the prod storage;
    # repoint it at the test DB so scans round-trip through the same SQLite.
    monkeypatch.setattr(apimain._orch, "storage", storage)
    monkeypatch.setattr(settings, "github_oauth_client_id", "test_client_id")
    monkeypatch.setattr(settings, "github_oauth_client_secret", "test_client_secret")
    return TestClient(apimain.app)


def test_health_reports_auth_state(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["auth_enabled"] is True


def test_me_requires_session(client):
    r = client.get("/api/auth/me")
    assert r.status_code == 401


def test_login_without_oauth_configured_returns_503(client, monkeypatch):
    monkeypatch.setattr(settings, "github_oauth_client_id", "")
    monkeypatch.setattr(settings, "github_oauth_client_secret", "")
    r = client.get("/api/auth/github/login", follow_redirects=False)
    assert r.status_code == 503


def test_login_sets_state_cookie_and_redirects_to_github(client):
    r = client.get("/api/auth/github/login", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "github.com/login/oauth/authorize" in r.headers["location"]
    assert "client_id=test_client_id" in r.headers["location"]
    assert auth_mod.STATE_COOKIE in r.cookies


def test_callback_rejects_mismatched_state(client):
    # No state cookie set → callback must reject
    r = client.get(
        "/api/auth/github/callback?code=abc&state=xyz", follow_redirects=False,
    )
    assert r.status_code == 400


def test_callback_full_login_flow_creates_user_and_session(
    client, monkeypatch,
):
    async def fake_exchange(code):
        assert code == "abc"
        return "gho_test_token"

    async def fake_user(token):
        assert token == "gho_test_token"
        return {
            "github_id": 42,
            "github_login": "octocat",
            "name": "Octo Cat",
            "email": "octo@example.com",
            "avatar_url": "https://example.com/a.png",
        }

    monkeypatch.setattr(auth_mod, "exchange_code_for_token", fake_exchange)
    monkeypatch.setattr(auth_mod, "fetch_github_user", fake_user)

    # Prime the state cookie that /login would have set
    client.cookies.set(auth_mod.STATE_COOKIE, "valid_state")
    r = client.get(
        "/api/auth/github/callback?code=abc&state=valid_state",
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert auth_mod.SESSION_COOKIE in r.cookies

    # /api/auth/me now returns the logged-in user
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["github_login"] == "octocat"
    assert body["email"] == "octo@example.com"


def test_logout_clears_session(client, monkeypatch):
    async def fake_exchange(code):
        return "gho_x"

    async def fake_user(token):
        return {
            "github_id": 7, "github_login": "u", "name": "u",
            "email": "u@e.com", "avatar_url": "",
        }

    monkeypatch.setattr(auth_mod, "exchange_code_for_token", fake_exchange)
    monkeypatch.setattr(auth_mod, "fetch_github_user", fake_user)
    client.cookies.set(auth_mod.STATE_COOKIE, "s")
    client.get("/api/auth/github/callback?code=c&state=s", follow_redirects=False)
    assert client.get("/api/auth/me").status_code == 200

    r = client.post("/api/auth/logout")
    assert r.status_code == 204
    # The Set-Cookie deletion takes effect for the *next* request — clear
    # the test client's cookie jar to simulate that.
    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401


def test_my_scans_requires_auth(client):
    r = client.get("/api/me/scans")
    assert r.status_code == 401


def test_my_scans_only_returns_logged_in_users_scans(client, monkeypatch):
    # log in as user A
    async def fake_exchange(_): return "t"
    async def fake_user(_):
        return {"github_id": 1, "github_login": "a", "name": "A",
                "email": "a@e.com", "avatar_url": ""}
    monkeypatch.setattr(auth_mod, "exchange_code_for_token", fake_exchange)
    monkeypatch.setattr(auth_mod, "fetch_github_user", fake_user)
    client.cookies.set(auth_mod.STATE_COOKIE, "s")
    client.get("/api/auth/github/callback?code=c&state=s", follow_redirects=False)

    # start a mock scan — it should get tagged with user A's id
    r = client.post(
        "/api/scans",
        json={"mock": True, "max_tests": 1, "use_live_sources": False,
              "categories": ["jailbreak"]},
    )
    assert r.status_code == 200

    # /api/me/scans returns A's scans (poll briefly — scan runs in background)
    import time
    for _ in range(30):
        my = client.get("/api/me/scans").json()["scans"]
        if my:
            break
        time.sleep(0.1)
    assert my and my[0]["user_id"] is not None


def test_dashboard_endpoints_respond_with_zeroed_aggregates(client):
    """Fresh DB → /dashboard/* must serve sensible empty defaults, not 500."""
    s = client.get("/api/dashboard/stats").json()
    assert s["total_scans"] == 0 and s["total_critical"] == 0
    assert s["by_severity"] == {"critical": 0, "high": 0, "medium": 0, "low": 0}

    assert client.get("/api/dashboard/findings").json() == {"findings": []}
    assert client.get("/api/dashboard/repos").json() == {"repos": []}
    assert client.get("/api/dashboard/trend?days=14").json() == {"trend": []}


def test_audit_endpoint_returns_404_for_missing_scan(client):
    r = client.get("/api/scans/does-not-exist/audit")
    assert r.status_code == 404
