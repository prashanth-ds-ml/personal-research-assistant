"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { RunStatus, RunSummary } from "@/lib/runs";
import { RunBadge, ago, isActive, progressText } from "@/components/run-status";
import { RunView } from "@/components/run-view";
import { ErrorCard } from "@/components/error-card";

type Tab = "all" | "running" | "waiting" | "done" | "issues";
const TABS: { key: Tab; label: string }[] = [
  { key: "all", label: "All" },
  { key: "running", label: "Running" },
  { key: "waiting", label: "Waiting" },
  { key: "done", label: "Done" },
  { key: "issues", label: "Stopped or failed" },
];

const matches = (t: Tab, s: RunStatus) =>
  t === "all" ||
  (t === "running" && (s === "running" || s === "stalled")) ||
  (t === "waiting" && s === "waiting") ||
  (t === "done" && s === "done") ||
  (t === "issues" && (s === "stopped" || s === "failed" || s === "lost"));

/** The Runs screen: the list on the left, the selected run on the right. */
export function RunsWorkspace({ initialId }: { initialId?: string }) {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<Tab>("all");
  const [sel, setSel] = useState<string | null>(initialId ?? null);

  const load = useCallback(async () => {
    try {
      const res = await fetch("/api/runs", { cache: "no-store" });
      if (!res.ok) throw new Error(`The server answered ${res.status}`);
      const body = (await res.json()) as { runs: RunSummary[] };
      setRuns(body.runs);
      setError("");
      return body.runs;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load runs");
      return null;
    }
  }, []);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const loop = async () => {
      const list = await load();
      if (!alive) return;
      timer = setTimeout(loop, list && list.some((r) => isActive(r.status)) ? 4000 : 15000);
    };
    loop();
    return () => {
      alive = false;
      if (timer) clearTimeout(timer);
    };
  }, [load]);

  // pick the newest run when nothing is selected yet
  const shown = useMemo(() => (runs ?? []).filter((r) => matches(tab, r.status)), [runs, tab]);
  const current = sel ?? shown[0]?.id ?? null;

  const choose = (id: string) => {
    setSel(id);
    window.history.replaceState(null, "", `/runs/${id}`);
  };

  const line = (r: RunSummary) =>
    r.waitingFor
      ? `Needs your ${r.waitingFor === "clarify" ? "answers" : r.waitingFor === "review" ? "choice of sources" : "approval"}`
      : r.status === "running" || r.status === "stalled"
        ? progressText(r.progress) || r.step
        : r.status === "done"
          ? `${r.progress.evidence ?? 0} verified facts`
          : r.error
            ? "Writing failed"
            : "";

  return (
    <div className="grid min-h-[calc(100vh-9rem)] gap-0 lg:grid-cols-[430px_minmax(0,1fr)]">
      <div className="min-w-0 border-border pr-0 lg:border-r lg:pr-7">
        <div className="kicker">The newsroom</div>
        <h1 className="mt-1 text-5xl leading-none">Runs</h1>
        <p className="mb-4 mt-3 text-sm text-muted">Everything started, including runs still going or waiting for you.</p>
        <div className="mb-4 flex flex-wrap gap-1.5">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              aria-pressed={tab === t.key}
              className={`rounded px-3 py-1.5 text-[13px] font-semibold ${tab === t.key ? "bg-accent-soft text-accent ring-1 ring-accent" : "border border-border hover:border-accent"}`}
            >
              {t.label}
            </button>
          ))}
        </div>
        {error && !runs && <ErrorCard error={error} onRetry={() => void load()} />}
        {!runs && !error && <p className="text-sm text-muted">Loading runs...</p>}
        {runs && runs.length === 0 && (
          <div className="py-8">
            <div className="font-serif text-4xl leading-tight">The press is quiet.</div>
            <p className="mt-2 font-serif text-xl italic text-muted">No runs yet. Start a deep research and it will show up here.</p>
            <Link href="/deep" className="mt-4 inline-block rounded bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground">
              New deep research
            </Link>
          </div>
        )}
        {runs && runs.length > 0 && shown.length === 0 && (
          <div className="py-8">
            <div className="font-serif text-4xl leading-tight">The press is quiet.</div>
            <p className="mt-2 font-serif text-xl italic text-muted">Nothing in this section right now.</p>
            <button type="button" onClick={() => setTab("all")} className="mt-4 rounded border border-foreground px-4 py-2 text-sm font-semibold">
              Show every run
            </button>
          </div>
        )}
        <ul className="flex flex-col gap-2.5">
          {shown.map((r) => (
            <li key={r.id}>
              <button
                type="button"
                onClick={() => choose(r.id)}
                className={`block w-full border px-4 py-3.5 text-left ${current === r.id ? "border-accent bg-accent-soft" : "border-border bg-surface hover:border-accent"}`}
              >
                <span className="mb-1.5 flex items-center gap-2">
                  <RunBadge status={r.status} />
                  <span className="text-[13px] text-muted">{ago(r.updatedAt)}</span>
                </span>
                <span className="block font-serif text-xl leading-snug">{r.goal.split("\n")[0].slice(0, 130) || "(no goal recorded)"}</span>
                {line(r) && <span className="mt-1 block text-[13px] text-muted">{line(r)}</span>}
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="min-w-0 pt-8 lg:pl-9 lg:pt-0">
        {current ? <RunView id={current} onChanged={load} /> : runs && runs.length > 0 ? <p className="font-serif text-2xl italic text-muted">Pick a run to see what it is doing.</p> : null}
      </div>
    </div>
  );
}
