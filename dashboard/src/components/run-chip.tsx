"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { RunSummary } from "@/lib/runs";
import { isActive } from "@/components/run-status";
import { stageOf, STAGES } from "@/lib/run-stages";

/** In the masthead on every page: is something working, or waiting for you? One click opens that run. */
export function RunChip() {
  const [run, setRun] = useState<RunSummary | null>(null);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const load = async () => {
      let busy = false;
      try {
        const res = await fetch("/api/runs", { cache: "no-store" });
        if (res.ok) {
          const body = (await res.json()) as { runs: RunSummary[] };
          // a run that needs you matters more than one that is just working
          const active = body.runs.filter((r) => isActive(r.status));
          const pick = active.find((r) => r.status === "waiting") ?? active[0] ?? null;
          if (alive) setRun(pick);
          busy = Boolean(pick);
        }
      } catch {
        /* keep the last reading */
      }
      if (alive) timer = setTimeout(load, busy ? 5000 : 20000);
    };
    void load();
    return () => {
      alive = false;
      if (timer) clearTimeout(timer);
    };
  }, []);

  if (!run) return null;
  const waiting = run.status === "waiting";
  const stage = stageOf(run.step);
  const label = waiting
    ? `Waiting for you · ${run.waitingFor === "clarify" ? "answer its questions" : run.waitingFor === "review" ? "choose sources" : "approve the plan"}`
    : `Run · stage ${Math.min(stage, 6) + 1} of 7, ${STAGES[Math.min(stage, 6)].toLowerCase()}`;
  return (
    <Link
      href={waiting ? `/deep?thread=${encodeURIComponent(run.id)}` : `/runs/${run.id}`}
      className={`flex items-center gap-2 rounded border px-3 py-1.5 text-xs font-semibold ${waiting ? "border-warning bg-warning-soft text-warning" : "border-accent bg-accent-soft text-accent"}`}
      title={run.goal.split("\n")[0].slice(0, 160)}
    >
      <span className={`inline-block h-2 w-2 rounded-full bg-current ${waiting ? "" : "animate-pulse"}`} aria-hidden />
      {label}
    </Link>
  );
}
