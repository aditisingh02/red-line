"""Static codebase scanner.

Scans AI-agent source code for insecure patterns (prompt-injection sinks,
hardcoded secrets, unsafe eval/deserialization, disabled TLS, …). Pure
stdlib + regex so it runs anywhere; cloning uses the `git` CLI and degrades
gracefully when git or the remote is unavailable.

Findings reuse the project's Severity vocabulary so the report shape matches
the runtime scanner's (`build_report`).
"""
from __future__ import annotations

import logging
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

log = logging.getLogger("redline.static_scanner")

# Directories that are never project code worth scanning.
_SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__",
    "dist", "build", ".mypy_cache", ".pytest_cache", ".tox", "site-packages",
    ".next", ".nuxt", "vendor", "third_party",
}
_SCAN_SUFFIXES = {".py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".rb", ".go", ".sh", ".env", ".yaml", ".yml"}
_MAX_FILE_BYTES = 1_000_000
# Inline suppression: a line containing this token is ignored.
_SUPPRESS = re.compile(r"#\s*redline:\s*ignore|//\s*redline:\s*ignore|nosec\b")


@dataclass
class Rule:
    id: str
    title: str
    severity: str  # critical | high | medium | low
    pattern: re.Pattern
    recommendation: str
    suffixes: tuple[str, ...] = (".py",)


@dataclass
class StaticFinding:
    rule_id: str
    title: str
    severity: str
    file: str
    line: int
    snippet: str
    recommendation: str

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "snippet": self.snippet,
            "recommendation": self.recommendation,
        }


def _r(s: str) -> re.Pattern:
    return re.compile(s)


# Ordered most-to-least severe. Patterns are intentionally conservative to
# keep the false-positive rate low on real agent codebases.
RULES: list[Rule] = [
    Rule("RL-SEC-001", "Hardcoded provider API key", "critical",
         _r(r"""(sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}|xox[baprs]-[A-Za-z0-9-]{10,})"""),
         "Move the secret to an environment variable or secrets manager; rotate the exposed key.",
         (".py", ".js", ".ts", ".env", ".yaml", ".yml", ".sh")),
    Rule("RL-SEC-002", "Assigned credential literal", "high",
         _r(r"""(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*["'][^"'\s]{8,}["']"""),
         "Load credentials from configuration/environment rather than source.",
         (".py", ".js", ".ts", ".rb", ".go")),
    Rule("RL-CODE-010", "Use of eval()/exec() on dynamic input", "critical",
         _r(r"\b(eval|exec)\s*\([^)]*[^\"')\s][^)]*\)"),
         "Never eval/exec model output or untrusted strings; parse explicitly instead.",
         (".py",)),
    Rule("RL-CODE-011", "Shell execution with shell=True / os.system", "critical",
         _r(r"(subprocess\.[a-z_]+\([^)]*shell\s*=\s*True|\bos\.(system|popen)\s*\()"),
         "Pass argument lists without a shell; never interpolate model output into commands.",
         (".py",)),
    Rule("RL-CODE-012", "Unsafe deserialization", "high",
         _r(r"(pickle\.loads?\s*\(|marshal\.loads\s*\(|yaml\.load\s*\((?![^)]*Safe))"),
         "Use yaml.safe_load and avoid pickle/marshal on data influenced by the model or users.",
         (".py",)),
    Rule("RL-NET-020", "TLS verification disabled", "high",  # redline: ignore
         _r(r"(verify\s*=\s*False|_create_unverified_context|InsecureRequestWarning)"),  # redline: ignore
         "Keep certificate verification enabled; pin or supply a CA bundle if needed.",
         (".py",)),
    Rule("RL-LLM-030", "Prompt built by interpolating untrusted input", "high",
         _r(r"""(?i)(system|prompt|messages|instruction)\s*=\s*f["'].*\{.+\}.*["']"""),
         "Keep system/developer instructions static; pass user input as a separate, clearly delimited turn.",
         (".py",)),
    Rule("RL-LLM-031", "User input concatenated into a prompt string", "medium",
         _r(r"""(?i)(prompt|system_prompt|instruction)\s*\+?=\s*.*\+\s*[A-Za-z_]\w*"""),
         "Avoid string concatenation for prompts; structure messages and sanitize user content.",
         (".py",)),
    Rule("RL-WEB-040", "CORS wildcard origin", "medium",
         _r(r"""allow_origins\s*=\s*\[\s*["']\*["']"""),
         "Restrict allowed origins to a known list; never combine '*' with credentials.",
         (".py",)),
    Rule("RL-WEB-041", "Debug server enabled", "medium",
         _r(r"(debug\s*=\s*True|FLASK_DEBUG\s*=\s*1)"),
         "Disable debug mode in any code path that can reach production.",
         (".py",)),
    Rule("RL-CRYPTO-050", "Weak hash for security use", "low",
         _r(r"hashlib\.(md5|sha1)\s*\("),
         "Use SHA-256+ for integrity/authentication; md5/sha1 only for non-security checksums.",
         (".py",)),
]

_SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def scan_path(root: str | Path) -> list[StaticFinding]:
    """Walk `root` and apply every rule line-by-line. Never raises on a bad file."""
    root = Path(root)
    findings: list[StaticFinding] = []
    base = root if root.is_dir() else root.parent
    targets = [root] if root.is_file() else _iter_files(root)
    for path in targets:
        try:
            if path.stat().st_size > _MAX_FILE_BYTES:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            log.debug("skip %s: %s", path, e)
            continue
        suffix = path.suffix.lower()
        rel = str(path.relative_to(base)) if _is_relative(path, base) else path.name
        for lineno, line in enumerate(text.splitlines(), 1):
            if _SUPPRESS.search(line):
                continue
            for rule in RULES:
                if suffix not in rule.suffixes:
                    continue
                if rule.pattern.search(line):
                    findings.append(StaticFinding(
                        rule_id=rule.id, title=rule.title, severity=rule.severity,
                        file=rel, line=lineno, snippet=line.strip()[:240],
                        recommendation=rule.recommendation,
                    ))
    findings.sort(key=lambda f: (_SEV_RANK[f.severity], f.file, f.line))
    return findings


def _iter_files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        if p.suffix.lower() in _SCAN_SUFFIXES:
            yield p


def _is_relative(p: Path, base: Path) -> bool:
    try:
        p.relative_to(base)
        return True
    except ValueError:
        return False


def _auth_url(repo_url: str, token: str) -> str:
    """Inject a token into an https git URL for private-repo cloning."""
    if not token or not repo_url.startswith("https://"):
        return repo_url
    parts = urlsplit(repo_url)
    netloc = f"x-access-token:{token}@{parts.hostname}"
    if parts.port:
        netloc += f":{parts.port}"
    return urlunsplit((parts.scheme, netloc, parts.path, "", ""))


def scan_repo(repo_url: str, github_token: str = "") -> tuple[list[StaticFinding], str | None]:
    """Shallow-clone `repo_url` to a tempdir and scan it.

    Returns (findings, error). On any clone failure, findings is [] and error
    is a human-readable string — the API surfaces it without crashing.
    """
    if not shutil.which("git"):
        return [], "git executable not found on the scanner host"
    tmp = tempfile.mkdtemp(prefix="redline-scan-")
    try:
        proc = subprocess.run(
            ["git", "clone", "--depth", "1", "--quiet",
             _auth_url(repo_url, github_token), tmp],
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0:
            lines = (proc.stderr or "").strip().splitlines()
            err = lines[-1] if lines else "git clone failed"
            # never echo the token back in an error
            return [], err.replace(github_token, "***") if github_token else err
        return scan_path(tmp), None
    except subprocess.TimeoutExpired:
        return [], "git clone timed out after 120s"
    except Exception as e:  # noqa: BLE001 — clone must never crash the API
        return [], f"{type(e).__name__}: {e}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _risk_level(by_sev: dict[str, int]) -> str:
    if by_sev["critical"]:
        return "HIGH — Critical insecure patterns found; do not ship."
    if by_sev["high"]:
        return "MEDIUM — High-risk patterns; remediate before release."
    if by_sev["medium"] or by_sev["low"]:
        return "LOW — Minor issues; review recommended."
    return "MINIMAL — No insecure patterns matched."


def build_static_report(target: str, findings: list[StaticFinding],
                        error: str | None = None) -> dict:
    """Report shaped like the runtime scanner's report for UI/CLI symmetry."""
    by_sev = {s: sum(1 for f in findings if f.severity == s)
              for s in ("critical", "high", "medium", "low")}
    return {
        "kind": "static",
        "target": target,
        "status": "error" if error else "completed",
        "error": error,
        "summary": {
            "files_flagged": len({f.file for f in findings}),
            "total_findings": len(findings),
            "by_severity": by_sev,
            "risk_level": _risk_level(by_sev),
        },
        "findings": [f.to_dict() for f in findings],
    }


def to_sarif(target: str, findings: list[StaticFinding]) -> dict:
    """SARIF 2.1.0 — ingestible by GitHub Code Scanning."""
    sarif_level = {"critical": "error", "high": "error",
                   "medium": "warning", "low": "note"}
    rules_seen: dict[str, dict] = {}
    results = []
    for f in findings:
        rules_seen.setdefault(f.rule_id, {
            "id": f.rule_id,
            "name": f.rule_id,
            "shortDescription": {"text": f.title},
            "helpUri": "https://owasp.org/www-project-top-10-for-large-language-model-applications/",
            "defaultConfiguration": {"level": sarif_level[f.severity]},
        })
        results.append({
            "ruleId": f.rule_id,
            "level": sarif_level[f.severity],
            "message": {"text": f"{f.title}: {f.recommendation}"},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": f.file},
                    "region": {"startLine": f.line, "snippet": {"text": f.snippet}},
                }
            }],
        })
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {
                "name": "Redline",
                "informationUri": "https://github.com/redline",
                "rules": list(rules_seen.values()),
            }},
            "results": results,
            "properties": {"target": target},
        }],
    }
