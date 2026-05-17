"""Redline CLI.

Examples:
  python cli.py scan --mock --max-tests 10
  python cli.py scan http://localhost:9000/chat --categories prompt_injection,jailbreak
  python cli.py serve
  python cli.py list-payloads
  python cli.py report <scan_id> --db redline.db
  python cli.py seed-demo
"""
from __future__ import annotations

import asyncio
import json
import sys

import typer

from redline.config import CATEGORIES, settings
from redline.models import ScanConfig
from redline.orchestrator import Orchestrator
from redline.report import build_report, render_text
from redline.sources import StaticSource
from redline.storage import Storage

app = typer.Typer(add_completion=False, help="Redline — AI agent red-teaming scanner")


def _parse_headers(items: list[str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for it in items or []:
        if ":" in it:
            k, v = it.split(":", 1)
            out[k.strip()] = v.strip()
    return out


@app.command()
def scan(
    target_url: str = typer.Argument("", help="Target agent endpoint (omit with --mock)"),
    categories: str = typer.Option("", help="Comma-separated; default = all 10"),
    max_tests: int = typer.Option(0, help="Cap number of payloads (0 = all)"),
    adapter: str = typer.Option("http", help="http|openai|anthropic|mock"),
    mock: bool = typer.Option(False, help="Use the offline mock target"),
    no_live: bool = typer.Option(False, help="Disable live payload sources"),
    header: list[str] = typer.Option(None, help="Auth header 'Key: Value' (repeatable)"),
    db: str = typer.Option("", help="SQLite path (default from config)"),
    json_out: bool = typer.Option(False, "--json", help="Print JSON report instead of text"),
) -> None:
    cfg = ScanConfig(
        target_url=target_url,
        auth_headers=_parse_headers(header),
        categories=[c.strip() for c in categories.split(",") if c.strip()],
        max_tests=max_tests or None,
        adapter=adapter,
        mock=mock,
        use_live_sources=not no_live,
    )
    storage = Storage(db or settings.redline_db_path)
    orch = Orchestrator(storage)

    async def _go() -> str:
        scan_id = None
        async for ev in orch.scan(cfg):
            e = ev.get("event")
            if e == "scan_start":
                scan_id = ev["scan_id"]
                typer.echo(f"▶ scan {scan_id} — categories: {','.join(ev['categories'])}")
            elif e == "payloads_ready":
                typer.echo(f"  payloads: {ev['count']}")
            elif e == "test_progress" and ev.get("status") == "running":
                typer.echo(f"  [{ev['index']}/{ev['total']}] {ev['category']} …", nl=False)
            elif e == "finding":
                mark = "✗" if ev["score"] >= 0.6 else "✓"
                typer.echo(f" {mark} {ev['verdict']} ({ev['score']:.2f})")
            elif e == "alert":
                typer.echo(f"  ⚠ ALERT [{ev['event_type']}] {ev['message']}")
            elif e == "scan_failed":
                typer.echo(f"✖ scan failed: {ev['reason']}")
            elif e == "scan_complete":
                typer.echo(f"■ done: {ev['summary']}")
        return scan_id or ""

    sid = asyncio.run(_go())
    if not sid:
        raise typer.Exit(1)
    report = build_report(storage, sid)
    typer.echo("")
    typer.echo(json.dumps(report, indent=2, default=str) if json_out else render_text(report))


@app.command("list-payloads")
def list_payloads() -> None:
    payloads = StaticSource().fetch([])
    by_cat: dict[str, int] = {}
    for p in payloads:
        by_cat[p.category] = by_cat.get(p.category, 0) + 1
    for c in CATEGORIES:
        typer.echo(f"  {c:24} {by_cat.get(c, 0)}")
    typer.echo(f"  {'TOTAL':24} {len(payloads)}")


@app.command()
def report(scan_id: str, db: str = typer.Option("", help="SQLite path")) -> None:
    storage = Storage(db or settings.redline_db_path)
    typer.echo(render_text(build_report(storage, scan_id)))


@app.command("seed-demo")
def seed_demo() -> None:
    from demo.seed_demo import main as seed_main

    seed_main()
    typer.echo("Seeded demo/demo_scan.db")


@app.command()
def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    import uvicorn

    uvicorn.run("api.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    if not settings.groq_api_key and "--json" not in sys.argv:
        typer.echo("ℹ no GROQ_API_KEY — using regex fallback scorer", err=True)
    app()
