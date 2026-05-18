import subprocess
import types

import redline.static_scanner as ss
from redline.static_scanner import (
    _auth_url,
    build_static_report,
    scan_path,
    scan_repo,
    to_sarif,
)

VULN_SRC = '''
import os, pickle, subprocess, hashlib

OPENAI_KEY = "sk-abcdefghijklmnopqrstuvwxyz0123456789"
api_key = "supersecretvalue123"

def run(model_out, user_input):
    eval(model_out)                              # RCE sink
    subprocess.run(model_out, shell=True)        # shell injection
    pickle.loads(model_out)                      # unsafe deser
    prompt = f"You are a bot. {user_input} do it"  # prompt injection sink
    hashlib.md5(user_input.encode())             # weak hash
    return prompt

SAFE = "literal"  # redline: ignore  eval(SAFE)
'''


def test_scan_path_flags_insecure_patterns(tmp_path):
    f = tmp_path / "agent.py"
    f.write_text(VULN_SRC)
    findings = scan_path(tmp_path)
    rules = {x.rule_id for x in findings}
    assert {"RL-SEC-001", "RL-CODE-010", "RL-CODE-011",
            "RL-CODE-012", "RL-LLM-030", "RL-CRYPTO-050"} <= rules
    # sorted critical-first
    assert findings[0].severity == "critical"


def test_suppression_comment_is_respected(tmp_path):
    f = tmp_path / "ok.py"
    f.write_text('token = "abcdefghij1234567890"  # redline: ignore\n')
    assert scan_path(tmp_path) == []


def test_skips_vendored_dirs(tmp_path):
    bad = tmp_path / "node_modules" / "x.py"
    bad.parent.mkdir(parents=True)
    bad.write_text('key = "sk-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"\n')
    assert scan_path(tmp_path) == []


def test_clean_repo_has_minimal_risk(tmp_path):
    (tmp_path / "clean.py").write_text("def add(a, b):\n    return a + b\n")
    report = build_static_report(str(tmp_path), scan_path(tmp_path))
    assert report["summary"]["total_findings"] == 0
    assert report["summary"]["risk_level"].startswith("MINIMAL")


def test_missing_path_returns_empty_not_raise(tmp_path):
    assert scan_path(tmp_path / "does-not-exist") == []


def test_oversized_file_is_skipped(tmp_path, monkeypatch):
    f = tmp_path / "big.py"
    f.write_text('k = "sk-abcdefghijklmnopqrstuvwxyz0123456789"\n')
    monkeypatch.setattr(ss, "_MAX_FILE_BYTES", 1)
    assert scan_path(tmp_path) == []


def test_auth_url_only_injects_for_https_token():
    assert _auth_url("https://github.com/o/r.git", "") == \
        "https://github.com/o/r.git"
    assert _auth_url("git@github.com:o/r.git", "tok") == "git@github.com:o/r.git"
    out = _auth_url("https://github.com/o/r.git", "tok")
    assert out == "https://x-access-token:tok@github.com/o/r.git"
    assert "tok@host:8443" in _auth_url("https://host:8443/o/r.git", "tok")


def test_scan_repo_no_git_binary(monkeypatch):
    monkeypatch.setattr(ss.shutil, "which", lambda _: None)
    findings, err = scan_repo("https://github.com/o/r.git")
    assert findings == [] and "git executable not found" in err


def test_scan_repo_clone_failure_scrubs_token(monkeypatch):
    monkeypatch.setattr(ss.shutil, "which", lambda _: "/usr/bin/git")

    def fake_run(*_a, **_kw):
        return types.SimpleNamespace(
            returncode=128,
            stderr="fatal: could not read from https://x-access-token:SECRET@h\n",
            stdout="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    findings, err = scan_repo("https://h/o/r.git", github_token="SECRET")
    assert findings == []
    assert "SECRET" not in err and "***" in err


def test_scan_repo_clone_timeout(monkeypatch):
    monkeypatch.setattr(ss.shutil, "which", lambda _: "/usr/bin/git")

    def boom(*_a, **_kw):
        raise subprocess.TimeoutExpired(cmd="git", timeout=120)

    monkeypatch.setattr(subprocess, "run", boom)
    findings, err = scan_repo("https://h/o/r.git")
    assert findings == [] and "timed out" in err


def test_sarif_shape(tmp_path):
    f = tmp_path / "a.py"
    f.write_text('k = "sk-abcdefghijklmnopqrstuvwxyz0123456789"\n')
    sarif = to_sarif("repo", scan_path(tmp_path))
    assert sarif["version"] == "2.1.0"
    run = sarif["runs"][0]
    assert run["tool"]["driver"]["name"] == "Redline"
    assert run["results"][0]["level"] == "error"
    assert run["results"][0]["locations"][0][
        "physicalLocation"]["region"]["startLine"] >= 1
