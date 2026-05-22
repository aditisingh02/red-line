import { useEffect, useRef, useState } from "react";
import { Activity, Loader2, ShieldAlert, ShieldCheck } from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Progress } from "@/components/ui/progress";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { api, streamScan, type Health, type StaticReport } from "@/lib/api";

const SEV_ORDER = ["critical", "high", "medium", "low"] as const;

function HealthPill() {
  const [h, setH] = useState<Health | null>(null);
  const [err, setErr] = useState(false);
  useEffect(() => {
    api.health().then(setH).catch(() => setErr(true));
  }, []);
  if (err)
    return (
      <Badge variant="muted" className="gap-1.5">
        <span className="h-1.5 w-1.5 rounded-full bg-muted-foreground" />
        backend offline
      </Badge>
    );
  if (!h) return <Badge variant="muted">checking…</Badge>;
  return (
    <Badge variant="outline" className="gap-1.5 font-mono">
      <span className="h-1.5 w-1.5 rounded-full bg-foreground" />
      v{h.version} · {h.scorer} judge · {h.status}
    </Badge>
  );
}

type Finding = {
  category: string;
  verdict: string;
  score: number;
  severity: string;
};

function LiveScan() {
  const [target, setTarget] = useState("");
  const [mock, setMock] = useState(true);
  const [categories, setCategories] = useState("prompt_injection,jailbreak");
  const [maxTests, setMaxTests] = useState(12);
  const [running, setRunning] = useState(false);
  const [scanId, setScanId] = useState<string | null>(null);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [findings, setFindings] = useState<Finding[]>([]);
  const [log, setLog] = useState<string[]>([]);
  const [risk, setRisk] = useState<string | null>(null);
  const unsub = useRef<() => void>();

  useEffect(() => () => unsub.current?.(), []);

  const addLog = (s: string) =>
    setLog((l) => [`${new Date().toLocaleTimeString()}  ${s}`, ...l].slice(0, 80));

  async function start() {
    setRunning(true);
    setFindings([]);
    setLog([]);
    setRisk(null);
    setProgress({ done: 0, total: 0 });
    try {
      const { scan_id } = await api.startScan({
        target_url: mock ? "" : target,
        mock,
        max_tests: maxTests,
        categories: categories
          .split(",")
          .map((c) => c.trim())
          .filter(Boolean),
        use_live_sources: false,
      });
      setScanId(scan_id);
      addLog(`scan ${scan_id} started`);
      unsub.current = streamScan(scan_id, (name, data) => {
        if (name === "payloads_ready") {
          setProgress({ done: 0, total: data.count });
          addLog(`payloads ready: ${data.count}`);
        } else if (name === "test_progress" && data.status !== "running") {
          setProgress((p) => ({ ...p, done: p.done + 1 }));
        } else if (name === "finding") {
          setFindings((f) => [
            {
              category: data.category,
              verdict: data.verdict,
              score: data.score,
              severity: data.severity,
            },
            ...f,
          ]);
        } else if (name === "alert") {
          addLog(`⚠ ALERT [${data.event_type}] ${data.message}`);
        } else if (name === "scan_failed") {
          addLog(`✖ failed: ${data.reason}`);
          setRunning(false);
        } else if (name === "scan_cancelled") {
          addLog("scan cancelled");
          setRunning(false);
        } else if (name === "scan_complete") {
          addLog(`■ done: ${JSON.stringify(data.summary)}`);
          setRunning(false);
          api
            .report(scan_id)
            .then((r: any) => setRisk(r?.summary?.risk_level ?? null))
            .catch(() => {});
        }
      });
    } catch (e) {
      addLog(`error: ${(e as Error).message}`);
      setRunning(false);
    }
  }

  async function cancel() {
    if (scanId) await api.cancelScan(scanId).catch(() => {});
    unsub.current?.();
    setRunning(false);
  }

  const pct = progress.total
    ? Math.round((progress.done / progress.total) * 100)
    : 0;

  return (
    <div className="grid gap-6 md:grid-cols-[320px_1fr]">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <Label>Mock target (offline)</Label>
            <Switch
              checked={mock}
              onCheckedChange={setMock}
              disabled={running}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Target URL</Label>
            <Input
              placeholder="http://localhost:9000/chat"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              disabled={mock || running}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Categories</Label>
            <Input
              value={categories}
              onChange={(e) => setCategories(e.target.value)}
              disabled={running}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Max tests</Label>
            <Input
              type="number"
              value={maxTests}
              onChange={(e) => setMaxTests(Number(e.target.value))}
              disabled={running}
            />
          </div>
          {running ? (
            <Button variant="outline" className="w-full" onClick={cancel}>
              Cancel scan
            </Button>
          ) : (
            <Button className="w-full" onClick={start}>
              Start scan
            </Button>
          )}
        </CardContent>
      </Card>

      <div className="space-y-6">
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-base">Progress</CardTitle>
            {running && (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            )}
          </CardHeader>
          <CardContent className="space-y-3">
            <Progress value={pct} />
            <div className="flex justify-between font-mono text-xs text-muted-foreground">
              <span>
                {progress.done}/{progress.total || "—"} tests
              </span>
              <span>{pct}%</span>
            </div>
            {risk && (
              <div className="flex items-center gap-2 rounded-md border border-border p-3 text-sm">
                {risk.startsWith("MINIMAL") ? (
                  <ShieldCheck className="h-4 w-4" />
                ) : (
                  <ShieldAlert className="h-4 w-4" />
                )}
                {risk}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Findings{" "}
              <span className="font-mono text-xs text-muted-foreground">
                ({findings.length})
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            {findings.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No findings yet.
              </p>
            ) : (
              <div className="divide-y divide-border">
                {findings.map((f, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between py-2 text-sm"
                  >
                    <span className="font-mono">{f.category}</span>
                    <span className="flex items-center gap-3">
                      <span className="text-muted-foreground">
                        {f.severity}
                      </span>
                      <Badge
                        variant={
                          f.score >= 0.6 ? "default" : "muted"
                        }
                        className="font-mono"
                      >
                        {f.verdict} {f.score.toFixed(2)}
                      </Badge>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Event log</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-48 overflow-auto font-mono text-[11px] leading-relaxed text-muted-foreground">
              {log.join("\n") || "—"}
            </pre>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StaticScan() {
  const [repo, setRepo] = useState("");
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [report, setReport] = useState<StaticReport | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setErr(null);
    setReport(null);
    try {
      setReport(await api.scanRepo(repo, token));
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Static repo scan</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1.5">
            <Label>Repository URL</Label>
            <Input
              placeholder="https://github.com/owner/repo.git"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              disabled={busy}
            />
          </div>
          <div className="space-y-1.5">
            <Label>GitHub token (private repos, optional)</Label>
            <Input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              disabled={busy}
            />
          </div>
          <Button onClick={run} disabled={busy || !repo}>
            {busy && <Loader2 className="h-4 w-4 animate-spin" />}
            Scan repository
          </Button>
          {err && (
            <p className="text-sm text-muted-foreground">Error: {err}</p>
          )}
        </CardContent>
      </Card>

      {report && (
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-base">{report.summary.risk_level}</CardTitle>
            <div className="flex gap-2">
              {SEV_ORDER.map((s) => (
                <Badge key={s} variant="outline" className="font-mono">
                  {s[0].toUpperCase()} {report.summary.by_severity[s] ?? 0}
                </Badge>
              ))}
            </div>
          </CardHeader>
          <CardContent>
            {report.error && (
              <p className="mb-4 text-sm text-muted-foreground">
                {report.error}
              </p>
            )}
            {report.findings.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                No insecure patterns matched.
              </p>
            ) : (
              <div className="divide-y divide-border">
                {report.findings.map((f, i) => (
                  <div key={i} className="py-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-mono">
                        {f.rule_id} · {f.file}:{f.line}
                      </span>
                      <Badge
                        variant={
                          ["critical", "high"].includes(f.severity)
                            ? "default"
                            : "muted"
                        }
                      >
                        {f.severity}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm">{f.title}</p>
                    <pre className="mt-1 overflow-auto rounded bg-muted px-2 py-1 font-mono text-[11px]">
                      {f.snippet}
                    </pre>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {f.recommendation}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function Dashboard() {
  return (
    <div className="min-h-screen">
      <Navbar />
      <main className="mx-auto max-w-5xl px-6 py-10">
        <div className="mb-8 flex items-center justify-between">
          <div>
            <h1 className="flex items-center gap-2 text-2xl font-semibold tracking-tight">
              <Activity className="h-5 w-5" />
              Dashboard
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Run a live red-team scan or statically scan a repository.
            </p>
          </div>
          <HealthPill />
        </div>

        <Tabs defaultValue="live">
          <TabsList>
            <TabsTrigger value="live">Live scan</TabsTrigger>
            <TabsTrigger value="static">Static repo scan</TabsTrigger>
          </TabsList>
          <TabsContent value="live">
            <LiveScan />
          </TabsContent>
          <TabsContent value="static">
            <StaticScan />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
