import hashlib
import hmac

from redline.integrations import github as gh


def _sign(secret: str, body: bytes) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_signature_roundtrip():
    body = b'{"hello":"world"}'
    assert gh.verify_signature("s3cret", body, _sign("s3cret", body))


def test_signature_rejects_tampering():
    body = b'{"a":1}'
    assert not gh.verify_signature("s3cret", body, _sign("wrong", body))
    assert not gh.verify_signature("s3cret", body, None)


def test_no_secret_skips_verification():
    assert gh.verify_signature("", b"anything", None)


def test_extract_pr_event_filters_actions():
    base = {
        "action": "opened",
        "pull_request": {"number": 7, "head": {"sha": "abc"}},
        "repository": {"full_name": "o/r", "clone_url": "https://x/o/r.git"},
    }
    ev = gh.extract_pr_event(base)
    assert ev["repo"] == "o/r" and ev["pr_number"] == 7
    assert gh.extract_pr_event({**base, "action": "closed"}) is None
    assert gh.extract_pr_event({"action": "opened"}) is None


def test_pr_comment_markdown_static_and_error():
    report = {
        "kind": "static",
        "summary": {"risk_level": "HIGH", "by_severity":
                    {"critical": 1, "high": 0, "medium": 0, "low": 0}},
        "findings": [{"severity": "critical", "rule_id": "RL-SEC-001",
                      "file": "a.py", "line": 3, "title": "Hardcoded key"}],
    }
    md = gh.pr_comment_markdown(report)
    assert "RL-SEC-001" in md and "a.py:3" in md and "HIGH" in md
    assert "failed" in gh.pr_comment_markdown({"error": "clone boom"})


def test_post_pr_comment_noop_without_token():
    assert gh.post_pr_comment("o/r", 1, "body", "") is False
