import { useEffect, useMemo, useState } from "react";
import { GitBranch, RefreshCw, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { api, type RepoSummary } from "@/lib/api";

function relTime(iso: string): string {
  const t = new Date(iso).getTime();
  const dt = Date.now() - t;
  const mins = Math.round(dt / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  return `${days}d ago`;
}

export function Repos({
  onRescan,
}: {
  onRescan?: (target_url: string) => void;
}) {
  const [repos, setRepos] = useState<RepoSummary[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    setErr(null);
    try {
      const r = await api.dashboardRepos();
      setRepos(r.repos);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const filtered = useMemo(() => {
    if (!q.trim()) return repos;
    const needle = q.toLowerCase();
    return repos.filter((r) => r.target_url.toLowerCase().includes(needle));
  }, [q, repos]);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-base">
            <GitBranch className="h-4 w-4" />
            Tracked repos &amp; endpoints
          </CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void refresh()}
            disabled={loading}
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Filter by URL"
              className="pl-9"
            />
          </div>

          {err && (
            <p className="text-sm text-muted-foreground">Error: {err}</p>
          )}

          {filtered.length === 0 && !err && (
            <p className="py-12 text-center text-sm text-muted-foreground">
              {repos.length === 0
                ? "Nothing here yet — every repo or endpoint you scan shows up here for tracking."
                : "No matches for that filter."}
            </p>
          )}

          <div className="grid gap-3 md:grid-cols-2">
            {filtered.map((r) => {
              const total =
                (r.passed ?? 0) + (r.failed ?? 0) + (r.critical ?? 0) || 1;
              const passPct = Math.round(((r.passed ?? 0) / total) * 100);
              const critPct = Math.round(((r.critical ?? 0) / total) * 100);
              return (
                <div
                  key={r.target_url}
                  className="flex flex-col gap-3 rounded-2xl border border-border bg-card/60 p-4"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="truncate font-mono text-sm">
                        {r.target_url || "(mock)"}
                      </div>
                      <div className="mt-1 font-mono text-[11px] text-muted-foreground">
                        last scan {relTime(r.last_scan_at)} · {r.last_status}
                      </div>
                    </div>
                    {onRescan && r.target_url && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => onRescan(r.target_url)}
                      >
                        Rescan
                      </Button>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-1.5">
                    <Badge variant="muted" className="font-mono">
                      {r.total_scans} scans
                    </Badge>
                    <Badge variant="muted" className="font-mono">
                      {r.passed ?? 0} pass
                    </Badge>
                    {(r.failed ?? 0) > 0 && (
                      <Badge className="border-orange-500/30 bg-orange-500/10 font-mono text-orange-300">
                        {r.failed} fail
                      </Badge>
                    )}
                    {(r.critical ?? 0) > 0 && (
                      <Badge className="border-redline-500/30 bg-redline-500/10 font-mono text-redline-300">
                        {r.critical} critical
                      </Badge>
                    )}
                  </div>

                  <div className="flex h-1.5 overflow-hidden rounded-full bg-card">
                    <div
                      className="bg-zinc-500/40"
                      style={{ width: `${passPct}%` }}
                    />
                    <div
                      className="bg-redline-500"
                      style={{ width: `${critPct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
