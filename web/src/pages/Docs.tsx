import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Boxes,
  CircleDot,
  Github,
  Server,
  Terminal,
  Workflow,
} from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { cn } from "@/lib/utils";

/* ------------------------------------------------------------------ *
 * Building blocks
 * ------------------------------------------------------------------ */

function CodeBlock({ label, code }: { label?: string; code: string }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      /* clipboard blocked — no-op */
    }
  }
  return (
    // Always-dark surface — keep all inner text light regardless of theme so
    // the labels stay readable in light mode too.
    <div className="group relative mt-4 overflow-hidden rounded-xl border border-white/10 bg-[#0c0c0c]">
      <div className="flex items-center justify-between border-b border-white/10 bg-white/[0.04] px-4 py-2">
        <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-400">
          {label ?? "shell"}
        </span>
        <button
          type="button"
          onClick={copy}
          className="font-mono text-[10px] uppercase tracking-[0.18em] text-zinc-400 transition-colors hover:text-redline-400"
        >
          {copied ? "copied" : "copy"}
        </button>
      </div>
      <pre className="overflow-x-auto px-4 py-3.5 text-[12.5px] leading-relaxed text-zinc-200">
        <code className="font-mono whitespace-pre">{code}</code>
      </pre>
    </div>
  );
}

function Section({
  id,
  index,
  icon: Icon,
  title,
  children,
}: {
  id: string;
  index: string;
  icon: typeof Server;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <motion.section
      id={id}
      initial={{ opacity: 0, y: 16 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.45 }}
      className="scroll-mt-24 border-t border-border/60 py-12 first:border-t-0"
    >
      <div className="mb-5 flex items-center gap-3">
        <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-redline-500/30 bg-redline-500/10 text-redline-400">
          <Icon className="h-4 w-4" />
        </span>
        <span className="font-mono text-xs text-muted-foreground">{index}</span>
        <h2 className="font-display text-2xl font-bold tracking-tight sm:text-3xl">
          {title}
        </h2>
      </div>
      <div className="prose-docs max-w-none space-y-3 text-sm leading-relaxed text-muted-foreground">
        {children}
      </div>
    </motion.section>
  );
}

function Endpoint({
  method,
  path,
  desc,
}: {
  method: "GET" | "POST";
  path: string;
  desc: string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-lg border border-border bg-card/50 px-3 py-2">
      <span
        className={cn(
          "rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold tracking-wider",
          method === "GET"
            ? "bg-mint/15 text-mint"
            : "bg-redline-500/15 text-redline-300",
        )}
      >
        {method}
      </span>
      <code className="font-mono text-[12.5px] text-foreground">{path}</code>
      <span className="ml-auto text-xs text-muted-foreground">{desc}</span>
    </div>
  );
}

/* ------------------------------------------------------------------ *
 * Side nav
 * ------------------------------------------------------------------ */

const TOC = [
  { id: "overview", label: "Overview" },
  { id: "prerequisites", label: "Prerequisites" },
  { id: "backend", label: "1 · Backend" },
  { id: "frontend", label: "2 · Frontend" },
  { id: "cli", label: "3 · CLI" },
  { id: "api", label: "4 · API reference" },
  { id: "ci", label: "5 · CI / GitHub" },
  { id: "config", label: "Config reference" },
];

function SideNav() {
  const [active, setActive] = useState("overview");
  useEffect(() => {
    const obs = new IntersectionObserver(
      (entries) => {
        for (const e of entries)
          if (e.isIntersecting) setActive(e.target.id);
      },
      { rootMargin: "-30% 0px -60% 0px" },
    );
    TOC.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) obs.observe(el);
    });
    return () => obs.disconnect();
  }, []);

  return (
    <nav className="sticky top-24 hidden h-fit w-48 shrink-0 lg:block">
      <span className="data-label">On this page</span>
      <ul className="mt-3 space-y-1 border-l border-border">
        {TOC.map((t) => (
          <li key={t.id}>
            <a
              href={`#${t.id}`}
              className={cn(
                "-ml-px block border-l-2 py-1 pl-3 text-sm transition-colors",
                active === t.id
                  ? "border-redline-500 text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              {t.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

/* ------------------------------------------------------------------ */

export default function Docs() {
  return (
    <div className="dot-grid relative min-h-screen bg-background">
      <Navbar />

      {/* hero */}
      <header className="border-b border-border/60">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <span className="data-label">Documentation</span>
          <h1 className="mt-3 font-display text-4xl font-extrabold tracking-[-0.03em] sm:text-6xl">
            Get Redline running
          </h1>
          <p className="mt-4 max-w-2xl text-base text-muted-foreground">
            Everything from zero to a live scan — backend, dashboard, CLI, the
            HTTP API, and CI. Copy-paste each block in order and you'll have the
            full stack up locally in a couple of minutes.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              to="/dashboard"
              className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              Open dashboard <ArrowRight className="h-4 w-4" />
            </Link>
            <a
              href="#backend"
              className="inline-flex items-center gap-1.5 rounded-md border border-border px-4 py-2 text-sm font-medium transition-colors hover:bg-accent"
            >
              Start with the backend
            </a>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-6xl gap-12 px-6 py-4">
        <SideNav />

        <main className="min-w-0 flex-1">
          <Section id="overview" index="00" icon={Boxes} title="Overview">
            <p>
              Redline is an autonomous red-teaming scanner for AI agents. It
              generates adversarial payloads across{" "}
              <strong className="text-foreground">10 attack categories</strong>,
              runs them against a live agent, judges every response with an LLM,
              and ships a structured security report.
            </p>
            <p>The stack has three pieces:</p>
            <ul className="ml-1 mt-2 space-y-2">
              {[
                ["Backend (FastAPI)", "Scan engine + HTTP API + SSE stream. Runs on :8001."],
                ["Dashboard (Vite/React)", "This UI. Live scans, history, code scan. Runs on :5173."],
                ["CLI (Typer)", "Same engine from the terminal — scan, scan-repo, report."],
              ].map(([t, d]) => (
                <li key={t} className="flex gap-2">
                  <CircleDot className="mt-0.5 h-3.5 w-3.5 shrink-0 text-redline-400" />
                  <span>
                    <strong className="text-foreground">{t}</strong> — {d}
                  </span>
                </li>
              ))}
            </ul>
          </Section>

          <Section
            id="prerequisites"
            index="01"
            icon={CircleDot}
            title="Prerequisites"
          >
            <p>You'll need:</p>
            <ul className="ml-1 mt-1 list-disc space-y-1 pl-4 marker:text-redline-500">
              <li><strong className="text-foreground">Python 3.11+</strong> for the backend and CLI</li>
              <li><strong className="text-foreground">Node 18+</strong> (CI uses 22) for the dashboard</li>
              <li>
                A <strong className="text-foreground">Fireworks AI</strong> API
                key for the LLM judge (optional — a regex judge is the fallback)
              </li>
            </ul>
            <p className="mt-3">Clone and enter the repo:</p>
            <CodeBlock code={"git clone <your-fork-url> red-line\ncd red-line"} />
          </Section>

          <Section id="backend" index="02" icon={Server} title="Backend & API">
            <p>
              <strong className="text-foreground">1. Create a virtualenv and install.</strong>
            </p>
            <CodeBlock
              code={
                "python3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt"
              }
            />
            <p className="mt-4">
              <strong className="text-foreground">2. Configure the LLM judge.</strong>{" "}
              Copy the example env and add your Fireworks key. Without a key
              Redline still runs using the offline regex judge.
            </p>
            <CodeBlock
              label=".env"
              code={
                "cp .env.example .env\n\n# in .env: the primary judge (preferred over Groq/Anthropic)\nFIREWORKS_API_KEY=fw_xxxxxxxxxxxxxxxxx\nFIREWORKS_MODEL=accounts/fireworks/models/kimi-k2p5\nFIREWORKS_BASE_URL=https://api.fireworks.ai/inference/v1"
              }
            />
            <p className="mt-4">
              <strong className="text-foreground">3. Serve the API on port 8001</strong>{" "}
              — the dashboard's dev proxy expects it there.
            </p>
            <CodeBlock code={".venv/bin/python cli.py serve --port 8001"} />
            <p className="mt-3">
              Verify it's healthy — the response shows which judge is active:
            </p>
            <CodeBlock
              code={
                'curl -s http://localhost:8001/api/health\n# {"status":"ok","scorer":"fireworks","auth_enabled":false}'
              }
            />
          </Section>

          <Section id="frontend" index="03" icon={Boxes} title="Frontend dashboard">
            <p>
              In a second terminal, install and run the dashboard. Vite proxies{" "}
              <code className="rounded bg-card px-1 py-0.5 font-mono text-[12px] text-foreground">/api</code>{" "}
              to the backend on <code className="rounded bg-card px-1 py-0.5 font-mono text-[12px] text-foreground">:8001</code>{" "}
              (override with <code className="rounded bg-card px-1 py-0.5 font-mono text-[12px] text-foreground">REDLINE_API_PORT</code>).
            </p>
            <CodeBlock
              label="web/"
              code={"cd web\nnpm install\nnpm run dev   # → http://localhost:5173"}
            />
            <p className="mt-3">
              Open{" "}
              <a
                href="http://localhost:5173"
                className="text-redline-400 underline-offset-4 hover:underline"
              >
                localhost:5173
              </a>
              . Production bundle:
            </p>
            <CodeBlock label="web/" code={"npm run build   # type-check + bundle to web/dist"} />
          </Section>

          <Section id="cli" index="04" icon={Terminal} title="CLI usage">
            <p>
              The CLI hits the same engine as the API. Run an offline scan
              against the built-in mock target — no keys, no network:
            </p>
            <CodeBlock
              code={"python cli.py scan --mock --max-tests 12 --json"}
            />
            <p className="mt-3">Scan a live agent endpoint by URL:</p>
            <CodeBlock
              code={
                'python cli.py scan https://agent.example/chat \\\n  --categories prompt_injection,jailbreak,data_exfiltration \\\n  --header "Authorization: Bearer $TOKEN"'
              }
            />
            <p className="mt-3">
              Static-scan a repo or local path (no calls to the agent) and emit
              SARIF for Code Scanning:
            </p>
            <CodeBlock
              code={
                "python cli.py scan-repo . --sarif redline.sarif --json"
              }
            />
            <p className="mt-3">Other commands:</p>
            <CodeBlock
              code={
                "python cli.py list-payloads        # show the payload library\npython cli.py report <scan_id>     # re-print a stored report\npython cli.py seed-demo            # load demo data into the DB"
              }
            />
          </Section>

          <Section id="api" index="05" icon={Server} title="API reference">
            <p>
              Base URL <code className="rounded bg-card px-1 py-0.5 font-mono text-[12px] text-foreground">http://localhost:8001</code>.
              Scans stream progress over Server-Sent Events.
            </p>
            <div className="mt-3 space-y-2">
              <Endpoint method="GET" path="/api/health" desc="liveness + active judge" />
              <Endpoint method="POST" path="/api/scans" desc="start a scan" />
              <Endpoint method="GET" path="/api/scans" desc="list scans" />
              <Endpoint method="GET" path="/api/scans/{id}/stream" desc="SSE progress" />
              <Endpoint method="GET" path="/api/scans/{id}/report" desc="full report" />
              <Endpoint method="POST" path="/api/scans/{id}/cancel" desc="cancel a run" />
              <Endpoint method="GET" path="/api/dashboard/stats" desc="overview metrics" />
              <Endpoint method="POST" path="/api/scan-repo" desc="static repo scan" />
            </div>
            <p className="mt-4">Kick off a scan over HTTP:</p>
            <CodeBlock
              code={
                "curl -X POST http://localhost:8001/api/scans \\\n  -H 'content-type: application/json' \\\n  -d '{\"mock\":true,\"max_tests\":12,\"categories\":[\"jailbreak\"]}'"
              }
            />
          </Section>

          <Section id="ci" index="06" icon={Workflow} title="CI / GitHub Action">
            <p>
              The repo ships{" "}
              <code className="rounded bg-card px-1 py-0.5 font-mono text-[12px] text-foreground">.github/workflows/redline.yml</code>:
              it static-scans the codebase on every PR and push to{" "}
              <code className="rounded bg-card px-1 py-0.5 font-mono text-[12px] text-foreground">main</code>,
              comments a summary, and fails the job on any{" "}
              <span className="text-redline-300">CRITICAL</span> finding.
            </p>
            <p className="mt-3">
              SARIF results surface under{" "}
              <strong className="text-foreground">Security → Code scanning</strong>.
              That upload is best-effort — if Code Scanning isn't enabled (or on
              fork PRs) the step is skipped, not failed. To enable it: repo{" "}
              <strong className="text-foreground">
                Settings → Code security → Code scanning → Set up
              </strong>
              .
            </p>
            <p className="mt-3">Reproduce the CI scan locally:</p>
            <CodeBlock
              code={"python cli.py scan-repo . --sarif redline.sarif --json"}
            />
          </Section>

          <Section id="config" index="07" icon={CircleDot} title="Config reference">
            <p>
              All settings load from <code className="rounded bg-card px-1 py-0.5 font-mono text-[12px] text-foreground">.env</code>{" "}
              (see <code className="rounded bg-card px-1 py-0.5 font-mono text-[12px] text-foreground">.env.example</code>).
              The judge is chosen in order: Fireworks → Groq → Anthropic → regex.
            </p>
            <div className="mt-4 overflow-hidden rounded-xl border border-border">
              <table className="w-full text-left text-sm">
                <thead className="bg-card/50">
                  <tr className="data-label [&>th]:px-4 [&>th]:py-2.5 [&>th]:font-normal">
                    <th>Variable</th>
                    <th>Purpose</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border [&_td]:px-4 [&_td]:py-2.5">
                  {[
                    ["FIREWORKS_API_KEY", "Primary LLM judge (preferred)"],
                    ["FIREWORKS_MODEL", "Judge model id"],
                    ["GROQ_API_KEY", "Fallback judge if Fireworks unset"],
                    ["ANTHROPIC_API_KEY", "Second fallback judge"],
                    ["REDLINE_DB_PATH", "SQLite path (default redline.db)"],
                    ["REDLINE_REQUEST_TIMEOUT", "Per-request timeout, seconds"],
                    ["GITHUB_TOKEN", "Private-repo clone + PR comments"],
                  ].map(([k, v]) => (
                    <tr key={k}>
                      <td>
                        <code className="font-mono text-[12.5px] text-redline-300">{k}</code>
                      </td>
                      <td className="text-muted-foreground">{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Section>

          {/* footer cta */}
          <div className="mt-12 flex flex-col items-start justify-between gap-4 border-t border-border/60 py-10 sm:flex-row sm:items-center">
            <div>
              <h3 className="font-display text-xl font-bold">Ready to scan?</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Backend on :8001, dashboard on :5173 — then hit the live tab.
              </p>
            </div>
            <div className="flex gap-3">
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
              >
                Open dashboard <ArrowRight className="h-4 w-4" />
              </Link>
              <a
                href="https://github.com/"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 rounded-md border border-border px-4 py-2 text-sm font-medium hover:bg-accent"
              >
                <Github className="h-4 w-4" /> Source
              </a>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
