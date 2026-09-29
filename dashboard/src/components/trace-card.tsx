import { ExternalLink, Clock, Zap } from "lucide-react";
import type { TraceSummary } from "@/lib/langsmith";
import { StatusBadge } from "@/components/status-badge";

const NODE_LABELS: Record<string, string> = {
  load_profile: "Load profile",
  retrieve_vault_context: "Retrieve vault context",
  generate_query: "Generate query",
  web_research: "Web research",
  summarize_sources: "Summarize sources",
  reflect_on_summary: "Reflect on summary",
  finalize_summary: "Finalize summary",
  update_profile: "Update profile",
  notify_complete: "Notify complete",
};

function formatMs(ms: number | null): string {
  if (ms === null) return "-";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function TraceCard({ trace }: { trace: TraceSummary }) {
  const totalMs = trace.endTime
    ? new Date(trace.endTime).getTime() - new Date(trace.startTime).getTime()
    : null;

  return (
    <div className="flex flex-col gap-4 rounded-2xl border border-border bg-surface p-5 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold">Trace</h2>
        <a
          href={trace.appUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-xs text-muted hover:text-accent"
        >
          Open in LangSmith
          <ExternalLink className="h-3 w-3" />
        </a>
      </div>

      <div className="flex flex-wrap items-center gap-4 text-xs text-muted">
        <StatusBadge status={trace.status === "success" ? "complete" : trace.status} />
        <span className="flex items-center gap-1">
          <Clock className="h-3.5 w-3.5" />
          {formatMs(totalMs)} total
        </span>
        {trace.totalTokens !== null && (
          <span className="flex items-center gap-1">
            <Zap className="h-3.5 w-3.5" />
            {trace.totalTokens.toLocaleString()} tokens
          </span>
        )}
      </div>

      <ol className="flex flex-col divide-y divide-border">
        {trace.steps.map((step, i) => (
          <li key={i} className="flex items-center justify-between py-2 text-sm">
            <span>{NODE_LABELS[step.node] ?? step.node}</span>
            <span className="text-xs text-muted">{formatMs(step.durationMs)}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
