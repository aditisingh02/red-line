from redline.static_scanner import (
    build_static_report,
    scan_path,
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
