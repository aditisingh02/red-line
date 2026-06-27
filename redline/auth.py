"""GitHub OAuth + session management.

The login flow is the standard authorization-code OAuth dance against
GitHub. Sessions are server-side: an opaque random token is stored in a
SQLite `sessions` row and sent to the browser as an HttpOnly cookie.

Works for both GitHub OAuth Apps and GitHub Apps (`/login/oauth/authorize`
is the same endpoint for both). Configure with
`GITHUB_OAUTH_CLIENT_ID` / `GITHUB_OAUTH_CLIENT_SECRET` in .env.
"""
from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx

from .config import settings
from .storage import Storage

log = logging.getLogger("redline.auth")

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_USER_EMAILS_URL = "https://api.github.com/user/emails"

# Login scope is intentionally minimal — repo access is configured per
# scan (via PAT or GitHub App installation), not granted at login time.
OAUTH_SCOPES = "read:user user:email"

SESSION_COOKIE = "redline_session"
STATE_COOKIE = "redline_oauth_state"
SESSION_TTL = timedelta(days=30)


@dataclass
class User:
    id: str
    github_id: int
    github_login: str
    name: str
    email: str
    avatar_url: str

    def public_dict(self) -> dict:
        return {
            "id": self.id,
            "github_id": self.github_id,
            "github_login": self.github_login,
            "name": self.name,
            "email": self.email,
            "avatar_url": self.avatar_url,
        }


def oauth_configured() -> bool:
    return bool(settings.github_oauth_client_id and settings.github_oauth_client_secret)


def build_authorize_url(state: str) -> str:
    """Pre-fills the GitHub authorize URL with our client id + state."""
    params = {
        "client_id": settings.github_oauth_client_id,
        "redirect_uri": settings.github_oauth_redirect_uri,
        "scope": OAUTH_SCOPES,
        "state": state,
        "allow_signup": "true",
    }
    return f"{GITHUB_AUTHORIZE_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> str:
    """Exchange the OAuth `code` for a user-to-server access token. Raises on failure."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            GITHUB_TOKEN_URL,
            data={
                "client_id": settings.github_oauth_client_id,
                "client_secret": settings.github_oauth_client_secret,
                "code": code,
                "redirect_uri": settings.github_oauth_redirect_uri,
            },
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        data = r.json()
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"github token exchange failed: {data.get('error') or data}")
    return token


async def fetch_github_user(token: str) -> dict:
    """Pull the GitHub user profile + primary verified email."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(GITHUB_USER_URL, headers=headers)
        r.raise_for_status()
        profile = r.json()
        email = profile.get("email") or ""
        if not email:
            r2 = await client.get(GITHUB_USER_EMAILS_URL, headers=headers)
            if r2.is_success:
                for e in r2.json():
                    if e.get("primary") and e.get("verified"):
                        email = e.get("email") or ""
                        break
    return {
        "github_id": int(profile["id"]),
        "github_login": profile.get("login") or "",
        "name": profile.get("name") or profile.get("login") or "",
        "email": email,
        "avatar_url": profile.get("avatar_url") or "",
    }


def new_state_token() -> str:
    return secrets.token_urlsafe(32)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def issue_session(storage: Storage, user_id: str) -> tuple[str, datetime]:
    """Create a fresh session and return (token, expires_at)."""
    token = new_session_token()
    expires = datetime.now(timezone.utc) + SESSION_TTL
    storage.save_session(token=token, user_id=user_id, expires_at=expires)
    return token, expires


def revoke_session(storage: Storage, token: str | None) -> None:
    if token:
        storage.delete_session(token)


def resolve_session(storage: Storage, token: str | None) -> User | None:
    """Look up the user behind a session cookie. Returns None on miss/expiry."""
    if not token:
        return None
    row = storage.get_session(token)
    if not row:
        return None
    expires = row.get("expires_at")
    if expires and _to_epoch(expires) < time.time():
        storage.delete_session(token)
        return None
    user_row = storage.get_user(row["user_id"])
    if not user_row:
        return None
    return User(
        id=user_row["id"],
        github_id=user_row["github_id"],
        github_login=user_row["github_login"] or "",
        name=user_row["name"] or "",
        email=user_row["email"] or "",
        avatar_url=user_row["avatar_url"] or "",
    )


def _to_epoch(ts: str | datetime) -> float:
    if isinstance(ts, datetime):
        return ts.timestamp()
    # SQLite stores ISO 8601 strings (see Storage.save_session)
    try:
        return datetime.fromisoformat(ts).timestamp()
    except ValueError:
        return 0.0
