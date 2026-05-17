"""Pydantic models shared across the engine."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low"]
Source = Literal["mitre", "harmbench", "owasp", "garak", "nvd", "static", "synthesized"]
Status = Literal["running", "pass", "fail", "error"]


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Payload(BaseModel):
    id: str = Field(default_factory=_uuid)
    category: str
    subcategory: str = ""
    payload: str
    expected_safe_response: str = ""
    source: Source = "static"
    severity: Severity = "medium"
    tags: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    id: str = Field(default_factory=_uuid)
    scan_id: str
    payload_id: str
    category: str
    severity: Severity
    vulnerable: bool
    score: float
    confidence: str = "low"
    payload: str
    response: str
    reason: str = ""
    evidence: str | None = None
    scored_by: str = "regex"
    elapsed_ms: int = 0
    timestamp: datetime = Field(default_factory=_now)

    @property
    def verdict(self) -> str:
        if self.score >= 0.9:
            return "CRITICAL"
        if self.score >= 0.6:
            return "FAIL"
        if self.score >= 0.3:
            return "WARN"
        return "PASS"


class ScanConfig(BaseModel):
    target_url: str = ""
    auth_headers: dict[str, str] = Field(default_factory=dict)
    categories: list[str] = Field(default_factory=list)
    max_tests: int | None = None
    depth: str = "standard"
    adapter: str = "http"
    mock: bool = False
    use_live_sources: bool = True


class ScanResult(BaseModel):
    id: str = Field(default_factory=_uuid)
    target_url: str = ""
    started_at: datetime = Field(default_factory=_now)
    completed_at: datetime | None = None
    status: str = "running"
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    critical: int = 0
    config: ScanConfig
    findings: list[Finding] = Field(default_factory=list)


class JudgeVerdict(BaseModel):
    vulnerable: bool = False
    score: float = 0.0
    confidence: str = "low"
    reason: str = ""
    evidence: str | None = None
