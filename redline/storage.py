"""SQLite persistence. Schema is created once at init and never altered mid-run."""
from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path

from .models import Finding, ScanResult

SCHEMA = """
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
  config_json TEXT
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
"""


class Storage:
    def __init__(self, db_path: str | Path = "redline.db") -> None:
        self.db_path = str(db_path)
        with closing(self._conn()) as c:
            c.executescript(SCHEMA)
            c.commit()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    # --- scans ---------------------------------------------------------
    def save_scan(self, scan: ScanResult) -> None:
        with closing(self._conn()) as c:
            c.execute(
                "INSERT OR REPLACE INTO scans VALUES (?,?,?,?,?,?,?,?,?,?)",
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
                ),
            )
            c.commit()

    def get_scan(self, scan_id: str) -> dict | None:
        with closing(self._conn()) as c:
            row = c.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone()
            return dict(row) if row else None

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
