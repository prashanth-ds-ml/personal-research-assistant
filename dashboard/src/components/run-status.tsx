import type { RunProgress, RunStatus } from "@/lib/runs";

const LABEL: Record<RunStatus, string> = {
  running: "Running",
  waiting: "Waiting for you",
  done: "Done",
  failed: "Failed",
  stopped: "Stopped",
  stalled: "Possibly stuck",
  lost: "Lost (backend restarted)",
};

const STYLE: Record<RunStatus, string> = {
  running: "bg-accent-soft text-accent",
  waiting: "bg-warning-soft text-warning",
  done: "bg-success-soft text-success",
  failed: "bg-warning-soft text-warning",
  stopped: "bg-surface-hover text-muted",
  stalled: "bg-warning-soft text-warning",
  lost: "bg-surface-hover text-muted",
};

export function RunBadge({ status }: { status: RunStatus }) {
  return <span className={`rounded px-2 py-0.5 text-[11px] font-medium ${STYLE[status]}`}>{LABEL[status]}</span>;
}

export const isActive = (s: RunStatus) => s === "running" || s === "waiting" || s === "stalled";

export function progressText(p: RunProgress): string {
  const parts: string[] = [];
  if (p.questions_total) parts.push(`${p.questions_done ?? 0}/${p.questions_total} questions`);
  if (p.evidence) parts.push(`${p.evidence} facts`);
  if (p.sections_total) parts.push(`${p.sections_done ?? 0}/${p.sections_total} sections`);
  return parts.join(" · ");
}

export function ago(iso: string): string {
  const ms = Date.now() - Date.parse(iso);
  if (!Number.isFinite(ms) || ms < 0) return "";
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  return h < 48 ? `${h} h ago` : `${Math.round(h / 24)} days ago`;
}

export function duration(startIso: string, endIso: string): string {
  const ms = Date.parse(endIso) - Date.parse(startIso);
  if (!Number.isFinite(ms) || ms < 0) return "";
  const m = Math.floor(ms / 60000);
  return m < 1 ? `${Math.round(ms / 1000)}s` : m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${m % 60} min`;
}
