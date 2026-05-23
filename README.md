# Redline

Autonomous AI-agent red-teaming scanner. Generates attack payloads, runs them
against a target agent, scores responses with an LLM judge, and produces a
structured security report.

Ships with a Python backend, a CLI, and a React/Vite dashboard (`web/`).

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

## Scanning another repo

Four supported paths, in order of setup cost. Pick by whether you want a one-off
result or continuous scanning, and by whether you have a server to host the API.

### 1. One-off CLI scan

Fastest. Clones the repo (shallow), scans, exits 1 on CRITICAL findings.

```bash
# public repo
.venv/bin/python cli.py scan-repo https://github.com/owner/repo --json > report.json

# private repo
.venv/bin/python cli.py scan-repo https://github.com/owner/repo --token ghp_xxx

# already-cloned local path (faster, no network)
.venv/bin/python cli.py scan-repo ./path/to/repo --sarif out.sarif --json > report.json
```

Output: text summary by default; `--json` prints the full report, `--sarif <path>`
also writes SARIF 2.1.0 for upload to GitHub Code Scanning. Status message
("`SARIF written to …`") is on stderr so stdout is pure JSON.

### 2. One-off API call

Same scan engine, useful when an HTTP boundary matters (web UI, scripts, other
services). Start the server first:

```bash
.venv/bin/python cli.py serve   # :8000
```

```bash
curl -X POST http://localhost:8000/api/scan-repo \
  -H "Content-Type: application/json" \
  -d '{"repo_url":"https://github.com/owner/repo","github_token":"ghp_xxx","format":"json"}'
# returns the same JSON report; pass "format":"sarif" for SARIF 2.1.0
```

### 3. GitHub Action in the target repo (per-PR, no server)

Drop a workflow file into the target repo. Redline isn't on PyPI yet, so the
job checks Redline out alongside the target repo and runs the CLI from there.
Copy this into `.github/workflows/redline.yml` of the target repo:

```yaml
name: Redline security scan
on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read
  security-events: write
  pull-requests: write
  actions: read

jobs:
  static-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/checkout@v4
        with:
          repository: <your-org>/red-line   # ← this repo
          path: .redline
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -r .redline/requirements.txt
      - run: python .redline/cli.py scan-repo . --sarif redline.sarif --json > report.json
        continue-on-error: true
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with: { sarif_file: redline.sarif }
      - run: |
          if [ "$(jq '.summary.by_severity.critical' report.json)" -gt 0 ]; then
            echo "::error::Redline found CRITICAL insecure patterns"; exit 1
          fi
```

This repo's own `.github/workflows/redline.yml` is a tighter version of the
same thing (it can `pip install -r requirements.txt` directly since Redline
lives in the same checkout).

### 4. GitHub App / webhook (central server, multi-repo)

Best when you want one Redline deployment to scan many repos automatically.

1. Host the API somewhere reachable from GitHub (e.g. `redline.yourdomain.com`).
2. Create a GitHub App with `Pull requests: read & write`, `Contents: read`,
   and the `pull_request` webhook event. Point its webhook URL at
   `https://redline.yourdomain.com/api/github/webhook` and set a webhook secret.
3. On the server, populate `.env`:
   ```
   GITHUB_TOKEN=<app-installation-token-or-PAT>
   GITHUB_WEBHOOK_SECRET=<same-secret>
   ```
4. Install the App on the repos you want scanned. Each PR opens/updates fires
   a webhook; Redline verifies the HMAC, clones, scans, and posts a comment.

Implementation: `api/main.py:201` and `redline/integrations/github.py`.

> ⚠️ If `GITHUB_WEBHOOK_SECRET` is empty, signature verification is skipped
> (`redline/integrations/github.py:28`). Acceptable for trusted internal
> deployments; never deploy a public webhook without a secret.

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

## Web dashboard

Vite + React + Tailwind. Live-scan tab streams findings over SSE; static-scan
tab runs the repo scanner; history tab lists past scans from the DB.

```bash
cd web
npm install
npm run dev          # http://localhost:5173, proxies /api -> :8000
npm run build        # type-check + production bundle to web/dist
```

See `web/README.md` for details.

## Notes / scope

Secrets live only in `.env` (gitignored).
