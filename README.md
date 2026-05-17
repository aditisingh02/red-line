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
| POST | `/api/scan-repo` | stub (static scanner out of scope in v1) |
| GET | `/api/health` | status |

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

Out of scope for this v1 backend build: React UI, GitHub App/Actions,
OpenTelemetry/Prometheus, static codebase scanner (`/api/scan-repo` returns a
stub). Secrets live only in `.env` (gitignored).
