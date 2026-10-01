"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Activity, ArrowRight } from "lucide-react";
import type { RunSummary } from "@/lib/runs";
import { RunBadge, ago, isActive, progressText } from "@/components/run-status";

/** The history of deep-research runs, including ones that are still going or never finished. Refreshes itself
 * while anything is active. */
export function RunsList() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const load = async () => {
      try {
        const res = await fetch("/api/runs", { cache: "no-store" });
        if (!res.ok) throw new Error(`The server answered ${res.status}`);
        const body = (await res.json()) as { runs: RunSummary[] };
        if (!alive) return;
        setRuns(body.runs);
        setError("");
        if (body.runs.some((r) => isActive(r.status))) timer = setTimeout(load, 4000);
      } catch (e) {
        if (!alive) return;
        setError(e instanceof Error ? e.message : "Could not load runs");
        timer = setTimeout(load, 10000);
      }
    };
    load();
    return () => {
      alive = false;
      if (timer) clearTimeout(timer);
    };
  }, []);

  if (error && !runs) {
    return (
      <div role="alert" className="rounded-xl border border-warning/30 bg-warning-soft px-4 py-3 text-sm text-warning">
        {error}
      </div>
    );
  }
  if (!runs) return <p className="text-sm text-muted">Loading runs...</p>;
  if (runs.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border py-20 text-center">
        <Activity className="h-8 w-8 text-muted" />
        <p className="text-sm text-muted">
          No deep-research runs yet.{" "}
          <Link href="/deep" className="font-medium text-accent hover:underline">
            Start one
          </Link>
        </p>
      </div>
    );
  }
  return (
    <ul className="flex flex-col gap-3">
      {runs.map((r) => (
        <li key={r.id}>
          <Link
            href={`/runs/${r.id}`}
            className="group flex items-center justify-between gap-4 rounded-2xl border border-border bg-surface p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-md"
          >
            <div className="flex min-w-0 flex-col gap-2">
              <div className="flex items-center gap-2">
                <span className="truncate font-medium">{r.goal.split("\n")[0].slice(0, 120) || "(no goal recorded)"}</span>
                <RunBadge status={r.status} />
              </div>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
                <span>{ago(r.updatedAt)}</span>
                {r.step && r.status !== "done" ? <span>step: {r.step}</span> : null}
                {progressText(r.progress) ? <span>{progressText(r.progress)}</span> : null}
                {r.waitingFor ? <span className="text-warning">needs your {r.waitingFor === "clarify" ? "answers" : r.waitingFor === "review" ? "choice of sources" : "approval"}</span> : null}
              </div>
            </div>
            <ArrowRight className="h-4 w-4 shrink-0 text-muted transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
          </Link>
        </li>
      ))}
    </ul>
  );
}
