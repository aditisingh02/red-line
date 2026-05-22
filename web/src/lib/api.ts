// Thin client over the Redline backend. Vite proxies /api -> :8000.

export type Health = {
  status: string;
  version: string;
  uptime: number;
  scorer: string;
};

export type ScanRequest = {
  target_url?: string;
  categories?: string[];
  max_tests?: number | null;
  mock?: boolean;
  use_live_sources?: boolean;
};

export type ScanSummary = {
  id: string;
  target_url: string;
  started_at: string;
  completed_at: string | null;
  status: string;
  total_tests: number;
  passed: number;
  failed: number;
  critical: number;
};

export type StaticReport = {
  kind: string;
  target: string;
  status: string;
  error: string | null;
  summary: {
    files_flagged: number;
    total_findings: number;
    by_severity: Record<string, number>;
    risk_level: string;
  };
  findings: {
    rule_id: string;
    title: string;
    severity: string;
    file: string;
    line: number;
    snippet: string;
    recommendation: string;
  }[];
};

async function j<T>(r: Response): Promise<T> {
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json() as Promise<T>;
}

export const api = {
  health: () => fetch("/api/health").then(j<Health>),

  startScan: (body: ScanRequest) =>
    fetch("/api/scans", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
    }).then(j<{ scan_id: string; status: string }>),

  listScans: (limit = 50) =>
    fetch(`/api/scans?limit=${limit}`).then(j<{ scans: ScanSummary[] }>),

  cancelScan: (id: string) =>
    fetch(`/api/scans/${id}/cancel`, { method: "POST" }).then(j),

  report: (id: string) =>
    fetch(`/api/scans/${id}/report`).then(j<Record<string, any>>),

  scanRepo: (repo_url: string, github_token = "") =>
    fetch("/api/scan-repo", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ repo_url, github_token }),
    }).then(j<StaticReport>),
};

// SSE stream of scan progress. Returns an unsubscribe fn.
const STREAM_EVENTS = [
  "scan_start",
  "payloads_ready",
  "test_progress",
  "finding",
  "alert",
  "scan_complete",
  "scan_failed",
  "scan_cancelled",
];

export function streamScan(
  id: string,
  onEvent: (name: string, data: any) => void,
): () => void {
  const es = new EventSource(`/api/scans/${id}/stream`);
  const handlers: Record<string, (e: MessageEvent) => void> = {};
  for (const name of STREAM_EVENTS) {
    const h = (e: MessageEvent) => {
      let parsed: any = e.data;
      try {
        parsed = JSON.parse(e.data);
      } catch {
        /* keep raw */
      }
      onEvent(name, parsed);
      if (["scan_complete", "scan_failed", "scan_cancelled"].includes(name)) {
        es.close();
      }
    };
    handlers[name] = h;
    es.addEventListener(name, h as EventListener);
  }
  es.onerror = () => es.close();
  return () => es.close();
}
