import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  AlertOctagon,
  Cpu,
  Gauge,
  ShieldAlert,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  api,
  type DashboardStats,
  type FlatFinding,
  type RepoSummary,
  type TrendPoint,
} from "@/lib/api";
import { cn } from "@/lib/utils";

const SEV_TONE: Record<string, string> = {
  critical: "bg-redline-500/15 text-redline-300 border-redline-500/30",
  high: "bg-orange-500/15 text-orange-300 border-orange-500/30",
  medium: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  low: "bg-zinc-500/15 text-zinc-300 border-zinc-500/30",
};

function MetricCard({
  label,
  value,
  hint,
  icon: Icon,
}: {
  label: string;
  value: string | number;
  hint?: string;
  icon: typeof Activity;
}) {
  return (
    <Card>
      <CardContent className="flex flex-col gap-2 p-5">
        <div className="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-muted-foreground">
          <Icon className="h-3.5 w-3.5" />
          {label}
        </div>
        <div className="font-mono text-3xl font-semibold tracking-tight text-foreground">
          {value}
        </div>
        {hint && <div className="text-xs text-muted-foreground">{hint}</div>}
      </CardContent>
    </Card>
  );
}

export function Overview({
  onOpenScan,
}: {
  onOpenScan?: (scanId: string) => void;
}) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [findings, setFindings] = useState<FlatFinding[]>([]);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [repos, setRepos] = useState<RepoSummary[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [s, f, t, r] = await Promise.all([
          api.dashboardStats(),
          api.dashboardFindings({ limit: 25 }),
          api.dashboardTrend(30),
          api.dashboardRepos(),
        ]);
        if (cancelled) return;
        setStats(s);
        setFindings(f.findings);
        setTrend(t.trend);
        setRepos(r.repos);
      } catch (e) {
        if (!cancelled) setErr((e as Error).message);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const sevTotal = useMemo(
    () =>
      stats
        ? stats.by_severity.critical +
          stats.by_severity.high +
          stats.by_severity.medium +
          stats.by_severity.low
        : 0,
    [stats],
  );

  const scorerEntries = Object.entries(stats?.by_scorer || {});
  const scorerTotal = scorerEntries.reduce((acc, [, n]) => acc + n, 0) || 1;

  if (err) {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          Couldn't load dashboard data: {err}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Metric cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label="Total scans"
          value={stats?.total_scans ?? "—"}
          hint={`${stats?.total_tests ?? 0} tests run`}
          icon={Activity}
        />
        <MetricCard
          label="Findings"
          value={sevTotal}
          hint={`${stats?.total_failed ?? 0} above FAIL threshold`}
          icon={ShieldAlert}
        />
        <MetricCard
          label="Critical"
          value={stats?.total_critical ?? 0}
          hint="severity = critical"
          icon={AlertOctagon}
        />
        <MetricCard
          label="Avg test latency"
          value={stats ? `${stats.avg_test_ms} ms` : "—"}
          hint="across all findings"
          icon={Gauge}
        />
      </div>

      {/* Trend + severity heatmap */}
      <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Scans over the last 30 days</CardTitle>
          </CardHeader>
          <CardContent>
            {trend.length === 0 ? (
              <p className="py-10 text-center text-sm text-muted-foreground">
                No scans yet — start one from the Live or Static tab.
              </p>
            ) : (
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trend}>
                    <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 3" vertical={false} />
                    <XAxis
                      dataKey="day"
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      stroke="hsl(var(--border))"
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      stroke="hsl(var(--border))"
                      allowDecimals={false}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "hsl(var(--card))",
                        border: "1px solid hsl(var(--border))",
                        fontSize: 12,
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="scans"
                      stroke="hsl(var(--red-500))"
                      strokeWidth={2}
                      dot={{ r: 2.5 }}
                      name="Scans"
                    />
                    <Line
                      type="monotone"
                      dataKey="critical"
                      stroke="hsl(var(--muted-foreground))"
                      strokeWidth={1.5}
                      dot={false}
                      name="Critical"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Severity mix</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {(["critical", "high", "medium", "low"] as const).map((sev) => {
                const n = stats?.by_severity[sev] ?? 0;
                const pct = sevTotal ? Math.round((n / sevTotal) * 100) : 0;
                return (
                  <div key={sev}>
                    <div className="mb-1 flex justify-between text-xs">
                      <span className="font-mono capitalize">{sev}</span>
                      <span className="font-mono text-muted-foreground">
                        {n} · {pct}%
                      </span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-card">
                      <div
                        className={cn(
                          "h-full rounded-full",
                          sev === "critical" && "bg-redline-500",
                          sev === "high" && "bg-orange-400",
                          sev === "medium" && "bg-amber-400",
                          sev === "low" && "bg-zinc-400",
                        )}
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
            {scorerEntries.length > 0 && (
              <div className="mt-6 border-t border-border pt-4">
                <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                  <Cpu className="h-3.5 w-3.5" />
                  Scorer backend
                </div>
                <div className="h-20">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={scorerEntries.map(([k, n]) => ({
                        name: k,
                        n,
                        pct: Math.round((n / scorerTotal) * 100),
                      }))}
                      layout="vertical"
                    >
                      <XAxis type="number" hide />
                      <YAxis
                        type="category"
                        dataKey="name"
                        tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                        width={70}
                        stroke="transparent"
                      />
                      <Tooltip
                        contentStyle={{
                          background: "hsl(var(--card))",
                          border: "1px solid hsl(var(--border))",
                          fontSize: 12,
                        }}
                      />
                      <Bar dataKey="n" fill="hsl(var(--red-500))" radius={4} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recent findings table */}
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="text-base">Recent findings</CardTitle>
          <span className="text-xs text-muted-foreground">
            {findings.length} most-recent
          </span>
        </CardHeader>
        <CardContent>
          {findings.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No findings yet.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="py-2 pr-3 font-medium">Severity</th>
                    <th className="py-2 pr-3 font-medium">Category</th>
                    <th className="py-2 pr-3 font-medium">Score</th>
                    <th className="py-2 pr-3 font-medium">Scored by</th>
                    <th className="py-2 pr-3 font-medium">Target</th>
                    <th className="py-2 pr-3 font-medium">When</th>
                  </tr>
                </thead>
                <tbody>
                  {findings.map((f) => (
                    <tr
                      key={f.id}
                      onClick={() => onOpenScan?.(f.scan_id)}
                      className="cursor-pointer border-b border-border/60 last:border-0 hover:bg-card/60"
                    >
                      <td className="py-2 pr-3">
                        <Badge
                          className={cn(
                            "border font-mono text-[10px]",
                            SEV_TONE[f.severity] ?? SEV_TONE.low,
                          )}
                        >
                          {f.severity}
                        </Badge>
                      </td>
                      <td className="py-2 pr-3 font-mono text-xs">
                        {f.category}
                      </td>
                      <td className="py-2 pr-3 font-mono text-xs">
                        {f.score.toFixed(2)}
                      </td>
                      <td className="py-2 pr-3 font-mono text-xs text-muted-foreground">
                        {f.scored_by}
                      </td>
                      <td className="py-2 pr-3 max-w-[280px] truncate font-mono text-xs">
                        {f.target_url || "(mock)"}
                      </td>
                      <td className="py-2 pr-3 font-mono text-[11px] text-muted-foreground">
                        {new Date(f.timestamp).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Per-repo cards (preview — full list lives in Repos tab) */}
      {repos.length > 0 && (
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="text-base">Tracked repos</CardTitle>
            <span className="text-xs text-muted-foreground">
              {repos.length} total
            </span>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {repos.slice(0, 6).map((r) => (
                <div
                  key={r.target_url}
                  className="flex flex-col gap-2 rounded-xl border border-border bg-card/60 p-4"
                >
                  <div className="truncate font-mono text-sm">
                    {r.target_url || "(mock)"}
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-muted-foreground">
                    <Badge variant="muted" className="font-mono">
                      {r.total_scans} scans
                    </Badge>
                    {r.critical > 0 && (
                      <Badge className="border-redline-500/30 bg-redline-500/10 text-redline-300">
                        {r.critical} critical
                      </Badge>
                    )}
                    <span className="font-mono">
                      last {new Date(r.last_scan_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
