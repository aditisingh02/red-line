# Redline

Autonomous AI-agent red-teaming scanner. Generates attack payloads, runs them
against a target agent, scores responses with an LLM judge, and produces a
structured security report.

This build is the **backend + CLI** (no React UI).

## Architecture

Orchestrator coordinates four sub-agents:

- **Payload Agent** — aggregates payloads from a static YAML library plus live
  sources (MITRE ATLAS, OWASP LLM Top 10, Hugging Face/AdvBench, Garak, NVD CVEs).
  Live sources are best-effort and degrade to static YAML on any failure.
- **Runner Agent** — executes payloads with a hard 10s timeout, exponential
  backoff on 429/5xx, and per-test isolation (one bad payload never aborts a scan).
- **Scorer Agent** — LLM-as-judge via **Groq** (`GROQ_API_KEY`), with a
  zero-config regex/keyword fallback. Results cached by `sha256(payload+response)`.
- **Monitor Agent** — baseline drift, hallucination/anomalous-tool-call signals,
  immutable audit log, real-time critical alerts.

10 attack categories: prompt_injection, jailbreak, role_confusion,
data_exfiltration, boundary_violation, adversarial_context, chain_manipulation,
hallucination_trigger, denial_of_service, social_engineering.

## Setup

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env      # add GROQ_API_KEY (optional; regex fallback works without it)
```

## CLI

```bash
# offline smoke (no network, no keys)
.venv/bin/python cli.py scan --mock --max-tests 10 --categories prompt_injection,jailbreak

# scan a live agent
.venv/bin/python cli.py scan http://localhost:9000/chat --categories prompt_injection,data_exfiltration

# inspect the payload library / a past scan / seed the demo DB
.venv/bin/python cli.py list-payloads
.venv/bin/python cli.py report <scan_id>
.venv/bin/python cli.py seed-demo
```

## API

```bash
.venv/bin/python cli.py serve          # http://localhost:8000
```

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/scans` | start a scan |
| GET | `/api/scans/{id}` | scan + findings + summary |
| GET | `/api/scans/{id}/stream` | SSE progress events |
| POST | `/api/scans/{id}/cancel` | cancel a scan |
| GET | `/api/scans/{id}/report?format=json` | full report |
| POST | `/api/scan-url` | freemium quick scan (capped, no auth) |
| POST | `/api/scan-repo` | static codebase scan (`format=json\|sarif`) |
| POST | `/api/github/webhook` | GitHub App: scans PRs, comments findings |
| GET | `/metrics` | Prometheus exposition (no-op if disabled) |
| GET | `/api/health` | status |

## Static codebase scanner

Regex/heuristic scan for insecure agent patterns (prompt-injection sinks,
hardcoded secrets, unsafe eval/deserialization, disabled TLS, …). Pure stdlib;
cloning uses the `git` CLI and degrades gracefully if git/the remote is
unavailable. Inline `# redline: ignore` suppresses a line.

```bash
.venv/bin/python cli.py scan-repo .                       # local path
.venv/bin/python cli.py scan-repo https://github.com/o/r --sarif out.sarif
```

Exit code is `1` when any CRITICAL finding is present (CI-friendly).

## GitHub App / Actions

- `.github/workflows/redline.yml` runs the static scan on every PR/push,
  uploads SARIF to GitHub Code Scanning, comments a summary, and fails the
  job on CRITICAL findings.
- `/api/github/webhook` verifies the `X-Hub-Signature-256` HMAC
  (`GITHUB_WEBHOOK_SECRET`), then scans the PR's repo and posts a comment
  (best-effort; needs `GITHUB_TOKEN`).

## Observability

- **Prometheus**: `GET /metrics` (scans, findings by severity, test-duration
  histogram, scorer-backend counter). Disable with `REDLINE_METRICS_ENABLED=false`.
- **OpenTelemetry**: traces export only when `OTEL_EXPORTER_OTLP_ENDPOINT` is
  set; otherwise spans are zero-cost no-ops.

Both backends are optional dependencies — absent → no-op, never an error.

## Demo

```bash
.venv/bin/python demo/vulnerable_agent.py        # weak target on :9000
.venv/bin/python cli.py scan http://localhost:9000/chat --max-tests 20
```

## Tests

```bash
.venv/bin/pytest -q
```

## Notes / scope

Out of scope for this build: React UI (backend + CLI only). Secrets live only
in `.env` (gitignored).
