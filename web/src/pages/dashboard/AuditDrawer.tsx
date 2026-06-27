import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { api, type AuditEvent } from "@/lib/api";
import { cn } from "@/lib/utils";

const EVENT_TONE: Record<string, string> = {
  scan_start: "bg-zinc-500/15 text-zinc-300",
  payloads_ready: "bg-zinc-500/15 text-zinc-300",
  scan_complete: "bg-emerald-500/15 text-emerald-300",
  scan_failed: "bg-orange-500/15 text-orange-300",
  critical_finding: "bg-redline-500/15 text-redline-300",
  hallucination_signal: "bg-amber-500/15 text-amber-300",
  anomalous_tool_call: "bg-amber-500/15 text-amber-300",
  behavioral_drift: "bg-amber-500/15 text-amber-300",
};

export function AuditDrawer({
  scanId,
  open,
  onClose,
}: {
  scanId: string | null;
  open: boolean;
  onClose: () => void;
}) {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !scanId) return;
    let cancelled = false;
    setLoading(true);
    setErr(null);
    setEvents([]);
    api
      .scanAudit(scanId)
      .then((r) => {
        if (!cancelled) setEvents(r.events);
      })
      .catch((e) => !cancelled && setErr((e as Error).message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [scanId, open]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    if (open) document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden
      />
      <aside
        role="dialog"
        aria-label="Scan audit timeline"
        className="fixed right-0 top-0 z-50 flex h-full w-full max-w-lg flex-col border-l border-border bg-background shadow-2xl"
      >
        <header className="flex items-center justify-between border-b border-border px-5 py-3">
          <div>
            <div className="text-sm font-semibold">Audit timeline</div>
            <div className="font-mono text-[11px] text-muted-foreground">
              {scanId ? `scan ${scanId.slice(0, 8)}` : "—"}
            </div>
          </div>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </Button>
        </header>

        <div className="flex-1 overflow-y-auto p-5">
          {loading && (
            <p className="text-sm text-muted-foreground">Loading…</p>
          )}
          {err && <p className="text-sm text-muted-foreground">Error: {err}</p>}
          {!loading && !err && events.length === 0 && (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No audit events recorded for this scan.
            </p>
          )}
          <ol className="relative ml-2 space-y-4 border-l border-border pl-5">
            {events.map((e) => {
              let data: Record<string, unknown> = {};
              try {
                data = JSON.parse(e.event_data);
              } catch {
                /* fall through */
              }
              return (
                <li key={e.id} className="relative">
                  <span className="absolute -left-[26px] top-1.5 h-2 w-2 rounded-full bg-redline-500" />
                  <div className="flex items-center justify-between">
                    <Badge
                      className={cn(
                        "font-mono text-[10px]",
                        EVENT_TONE[e.event_type] ?? "bg-card text-foreground",
                      )}
                    >
                      {e.event_type}
                    </Badge>
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {new Date(e.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  {Object.keys(data).length > 0 && (
                    <pre className="mt-2 overflow-x-auto rounded-md border border-border bg-card/60 p-2 font-mono text-[11px] text-muted-foreground">
                      {JSON.stringify(data, null, 2)}
                    </pre>
                  )}
                </li>
              );
            })}
          </ol>
        </div>
      </aside>
    </>
  );
}
