"""SQLite persistence. Schema is created at init and lightly migrated on open."""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .models import Finding, ScanResult

BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
  id TEXT PRIMARY KEY,
  target_url TEXT,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  status TEXT,
  total_tests INTEGER,
  passed INTEGER,
  failed INTEGER,
  critical INTEGER,
  config_json TEXT,
  user_id TEXT
);
CREATE TABLE IF NOT EXISTS findings (
  id TEXT PRIMARY KEY,
  scan_id TEXT REFERENCES scans(id),
  payload_id TEXT,
  category TEXT,
  severity TEXT,
  vulnerable BOOLEAN,
  score REAL,
  confidence TEXT,
  payload TEXT,
  response TEXT,
  reason TEXT,
  evidence TEXT,
  scored_by TEXT,
  elapsed_ms INTEGER,
  timestamp TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scan_id TEXT,
  event_type TEXT,
  event_data TEXT,
  timestamp TIMESTAMP
);
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  github_id INTEGER UNIQUE,
  github_login TEXT,
  name TEXT,
  email TEXT,
  avatar_url TEXT,
  access_token TEXT,
  created_at TIMESTAMP,
  last_login_at TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sessions (
  token TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  expires_at TIMESTAMP,
  created_at TIMESTAMP
);
"""

INDEXES = """
CREATE INDEX IF NOT EXISTS idx_scans_user_id ON scans(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
"""


class Storage:
    def __init__(self, db_path: str | Path = "redline.db") -> None:
        self.db_path = str(db_path)
        with closing(self._conn()) as c:
            c.executescript(BASE_SCHEMA)
            self._migrate_scans_user_id(c)
            c.executescript(INDEXES)
            c.commit()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _migrate_scans_user_id(c: sqlite3.Connection) -> None:
        """Defensive ALTER for older DBs created before the users feature."""
        cols = {r["name"] for r in c.execute("PRAGMA table_info(scans)")}
        if "user_id" not in cols:
            c.execute("ALTER TABLE scans ADD COLUMN user_id TEXT")

    # --- scans ---------------------------------------------------------
    def save_scan(self, scan: ScanResult) -> None:
        with closing(self._conn()) as c:
            c.execute(
                "INSERT OR REPLACE INTO scans (id, target_url, started_at, "
                "completed_at, status, total_tests, passed, failed, critical, "
                "config_json, user_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    scan.id,
                    scan.target_url,
                    scan.started_at.isoformat(),
                    scan.completed_at.isoformat() if scan.completed_at else None,
                    scan.status,
                    scan.total_tests,
                    scan.passed,
                    scan.failed,
                    scan.critical,
                    scan.config.model_dump_json(),
                    scan.user_id,
                ),
            )
            c.commit()

    def get_scan(self, scan_id: str) -> dict | None:
        with closing(self._conn()) as c:
            row = c.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone()
            return dict(row) if row else None

    def list_scans(self, limit: int = 50, user_id: str | None = None) -> list[dict]:
        lim = max(1, min(int(limit), 500))
        cols = (
            "id, target_url, started_at, completed_at, status, "
            "total_tests, passed, failed, critical, user_id"
        )
        with closing(self._conn()) as c:
            if user_id is None:
                rows = c.execute(
                    f"SELECT {cols} FROM scans "
                    "ORDER BY started_at DESC LIMIT ?",
                    (lim,),
                ).fetchall()
            else:
                rows = c.execute(
                    f"SELECT {cols} FROM scans WHERE user_id = ? "
                    "ORDER BY started_at DESC LIMIT ?",
                    (user_id, lim),
                ).fetchall()
            return [dict(r) for r in rows]

    # --- findings ------------------------------------------------------
    def save_finding(self, f: Finding) -> None:
        with closing(self._conn()) as c:
            c.execute(
                "INSERT OR REPLACE INTO findings VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    f.id, f.scan_id, f.payload_id, f.category, f.severity,
                    f.vulnerable, f.score, f.confidence, f.payload, f.response,
                    f.reason, f.evidence, f.scored_by, f.elapsed_ms,
                    f.timestamp.isoformat(),
                ),
            )
            c.commit()

    def get_findings(self, scan_id: str) -> list[dict]:
        with closing(self._conn()) as c:
            rows = c.execute(
                "SELECT * FROM findings WHERE scan_id=? ORDER BY score DESC", (scan_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    # --- audit log -----------------------------------------------------
    def audit(self, scan_id: str, event_type: str, event_data: dict) -> None:
        with closing(self._conn()) as c:
            c.execute(
                "INSERT INTO audit_log (scan_id, event_type, event_data, timestamp) "
                "VALUES (?,?,?,?)",
                (scan_id, event_type, json.dumps(event_data, default=str),
                 datetime.now(timezone.utc).isoformat()),
            )
            c.commit()

    def get_audit(self, scan_id: str) -> list[dict]:
        with closing(self._conn()) as c:
            rows = c.execute(
                "SELECT * FROM audit_log WHERE scan_id=? ORDER BY id", (scan_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    # --- users ---------------------------------------------------------
    def upsert_user_from_github(
        self,
        github_id: int,
        github_login: str,
        name: str,
        email: str,
        avatar_url: str,
        access_token: str,
    ) -> dict:
        """Insert a new user or refresh the existing one keyed by github_id."""
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._conn()) as c:
            existing = c.execute(
                "SELECT id FROM users WHERE github_id=?", (github_id,)
            ).fetchone()
            if existing:
                c.execute(
                    "UPDATE users SET github_login=?, name=?, email=?, "
                    "avatar_url=?, access_token=?, last_login_at=? WHERE id=?",
                    (github_login, name, email, avatar_url,
                     access_token, now, existing["id"]),
                )
                user_id = existing["id"]
            else:
                user_id = str(uuid.uuid4())
                c.execute(
                    "INSERT INTO users (id, github_id, github_login, name, "
                    "email, avatar_url, access_token, created_at, last_login_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (user_id, github_id, github_login, name, email,
                     avatar_url, access_token, now, now),
                )
            c.commit()
            row = c.execute(
                "SELECT * FROM users WHERE id=?", (user_id,)
            ).fetchone()
            return dict(row)

    def get_user(self, user_id: str) -> dict | None:
        with closing(self._conn()) as c:
            row = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            return dict(row) if row else None

    # --- sessions ------------------------------------------------------
    def save_session(self, token: str, user_id: str, expires_at: datetime) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._conn()) as c:
            c.execute(
                "INSERT OR REPLACE INTO sessions (token, user_id, expires_at, "
                "created_at) VALUES (?,?,?,?)",
                (token, user_id, expires_at.isoformat(), now),
            )
            c.commit()

    def get_session(self, token: str) -> dict | None:
        with closing(self._conn()) as c:
            row = c.execute(
                "SELECT * FROM sessions WHERE token=?", (token,)
            ).fetchone()
            return dict(row) if row else None

    def delete_session(self, token: str) -> None:
        with closing(self._conn()) as c:
            c.execute("DELETE FROM sessions WHERE token=?", (token,))
            c.commit()

    def purge_expired_sessions(self) -> int:
        """Best-effort cleanup of expired sessions. Returns rows deleted."""
        now = datetime.now(timezone.utc).isoformat()
        with closing(self._conn()) as c:
            cur = c.execute("DELETE FROM sessions WHERE expires_at < ?", (now,))
            c.commit()
            return cur.rowcount or 0

    # --- aggregates for dashboard --------------------------------------
    @staticmethod
    def _scope(user_id: str | None) -> tuple[str, tuple]:
        """SQL clause + params to scope a query by user_id (or no scope)."""
        if user_id is None:
            return "", ()
        return " WHERE s.user_id = ? ", (user_id,)

    def aggregate_stats(self, user_id: str | None = None) -> dict:
        """Totals for the overview cards. Scoped to user when provided."""
        scope, params = self._scope(user_id)
        finding_scope = (
            "" if user_id is None
            else (" WHERE f.scan_id IN (SELECT id FROM scans WHERE user_id = ?) ")
        )
        finding_params: tuple = () if user_id is None else (user_id,)
        with closing(self._conn()) as c:
            scans = c.execute(
                f"SELECT COUNT(*) AS n, COALESCE(SUM(total_tests), 0) AS tests, "
                f"COALESCE(SUM(critical), 0) AS crit, COALESCE(SUM(failed), 0) AS failed "
                f"FROM scans s {scope}",
                params,
            ).fetchone()
            findings = c.execute(
                f"SELECT severity, COUNT(*) AS n FROM findings f "
                f"{finding_scope} GROUP BY severity",
                finding_params,
            ).fetchall()
            scorers = c.execute(
                f"SELECT COALESCE(scored_by, 'unknown') AS scored_by, COUNT(*) AS n "
                f"FROM findings f {finding_scope} GROUP BY scored_by",
                finding_params,
            ).fetchall()
            avg_latency = c.execute(
                f"SELECT COALESCE(AVG(elapsed_ms), 0) AS avg_ms FROM findings f "
                f"{finding_scope}",
                finding_params,
            ).fetchone()
        by_sev = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for r in findings:
            sev = r["severity"] or "low"
            by_sev[sev] = by_sev.get(sev, 0) + r["n"]
        return {
            "total_scans": int(scans["n"] or 0),
            "total_tests": int(scans["tests"] or 0),
            "total_failed": int(scans["failed"] or 0),
            "total_critical": int(scans["crit"] or 0),
            "by_severity": by_sev,
            "by_scorer": {r["scored_by"]: int(r["n"]) for r in scorers},
            "avg_test_ms": int(avg_latency["avg_ms"] or 0),
        }

    def list_findings(
        self,
        user_id: str | None = None,
        limit: int = 50,
        severity: str | None = None,
        category: str | None = None,
    ) -> list[dict]:
        """Flat findings table, joined with scan target_url, newest first."""
        lim = max(1, min(int(limit), 500))
        where = ["1=1"]
        params: list = []
        if user_id is not None:
            where.append("s.user_id = ?")
            params.append(user_id)
        if severity:
            where.append("f.severity = ?")
            params.append(severity)
        if category:
            where.append("f.category = ?")
            params.append(category)
        sql = (
            "SELECT f.id, f.scan_id, f.category, f.severity, f.score, "
            "f.scored_by, f.confidence, f.elapsed_ms, f.timestamp, "
            "s.target_url FROM findings f "
            "JOIN scans s ON s.id = f.scan_id "
            f"WHERE {' AND '.join(where)} "
            "ORDER BY f.timestamp DESC LIMIT ?"
        )
        params.append(lim)
        with closing(self._conn()) as c:
            rows = c.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def list_repos(self, user_id: str | None = None) -> list[dict]:
        """Group scans by target_url. Returns one row per repo with aggregates."""
        scope = "" if user_id is None else "WHERE s.user_id = ?"
        params: tuple = () if user_id is None else (user_id,)
        sql = (
            "SELECT COALESCE(s.target_url, '') AS target_url, "
            "COUNT(*) AS total_scans, "
            "MAX(s.started_at) AS last_scan_at, "
            "MAX(s.status) AS last_status, "
            "SUM(s.critical) AS critical, "
            "SUM(s.failed) AS failed, "
            "SUM(s.passed) AS passed "
            "FROM scans s "
            f"{scope} "
            "GROUP BY target_url "
            "ORDER BY last_scan_at DESC"
        )
        with closing(self._conn()) as c:
            rows = c.execute(sql, params).fetchall()
            return [dict(r) for r in rows]

    def scans_over_time(
        self, user_id: str | None = None, days: int = 30,
    ) -> list[dict]:
        """Daily scan + critical-finding counts for the trend chart."""
        scope = "" if user_id is None else "AND s.user_id = ?"
        params: list = [] if user_id is None else [user_id]
        sql = (
            "SELECT DATE(s.started_at) AS day, "
            "COUNT(*) AS scans, "
            "SUM(s.critical) AS critical "
            "FROM scans s "
            "WHERE DATE(s.started_at) >= DATE('now', ?) "
            f"{scope} "
            "GROUP BY day ORDER BY day ASC"
        )
        params.insert(0, f"-{max(1, min(int(days), 365))} days")
        with closing(self._conn()) as c:
            rows = c.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
