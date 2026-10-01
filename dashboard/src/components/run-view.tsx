"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Circle, FileText, Globe, Loader2, RotateCcw, Square } from "lucide-react";
import type { CollectedRow, RunDetail, UsedSource } from "@/lib/runs";
import { safeHref } from "@/lib/safe-href";
import { RunBadge, ago, duration, isActive } from "@/components/run-status";

// The pipeline as the user thinks of it. Each backend step belongs to one stage.
const STAGES = ["Library", "Questions", "Plan", "Sources", "Research", "Write", "Save"] as const;
const STAGE_OF: Record<string, number> = {
  library: 0, questions: 1, clarify: 1, plan: 2, approve: 2, discover: 3, review: 3, collect: 3, research: 4, write: 5, save: 6, done: 7,
};

function reportSlug(path: string): string | null {
  const file = path.split(/[\\/]/).pop();
  return file ? file.replace(/\.md$/, "") : null;
}

function Bar({ label, done, total }: { label: string; done: number; total: number }) {
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;
  return (
    <div className="flex flex-col gap-1">
      <div className="flex justify-between text-xs text-muted">
        <span>{label}</span>
        <span>
          {done}/{total}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-surface-hover" role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
        <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

const isPdf = (kind: string) => kind === "pdf" || kind === "paper";

function Link2Row({ title, url }: { title: string; url: string }) {
  return url ? (
    <a href={safeHref(url)} target="_blank" rel="noopener noreferrer nofollow" className="font-medium hover:text-accent hover:underline">
      {title}
    </a>
  ) : (
    <span className="font-medium">{title}</span>
  );
}

/** Two lists side by side: PDFs and papers on one side, web pages on the other, so it is clear what the run is
 * pulling in and what the report leans on. `rows` come either from the collector (with a status) or from the report
 * (with fact counts). */
function SourceColumns({ title, hint, collected, used }: { title: string; hint: string; collected?: CollectedRow[]; used?: UsedSource[] }) {
  const pdfs = (collected ?? []).filter((c) => isPdf(c.kind));
  const pages = (collected ?? []).filter((c) => !isPdf(c.kind));
  const usedPdfs = (used ?? []).filter((u) => isPdf(u.kind));
  const usedPages = (used ?? []).filter((u) => u.kind === "web");
  const usedOther = (used ?? []).filter((u) => !isPdf(u.kind) && u.kind !== "web");
  const empty = <li className="text-muted">None</li>;
  const col = (label: string, icon: React.ReactNode, items: React.ReactNode[], count: number) => (
    <div className="flex flex-col gap-2">
      <h3 className="flex items-center gap-1.5 text-xs font-medium text-muted">
        {icon}
        {label} ({count})
      </h3>
      <ul className="flex flex-col gap-1.5 text-xs">{items.length ? items : empty}</ul>
    </div>
  );
  const collectedItem = (c: CollectedRow, i: number) => (
    <li key={`${c.url}-${i}`}>
      <Link2Row title={c.title || c.url} url={c.url} />
      <span className={`ml-2 ${c.status === "saved" ? "text-success" : "text-warning"}`}>
        {c.status === "saved" ? "saved" : c.status}
        {c.reason ? `: ${c.reason}` : ""}
      </span>
    </li>
  );
  const usedItem = (u: UsedSource, i: number) => (
    <li key={`${u.url}-${u.title}-${i}`}>
      <Link2Row title={u.title} url={u.url} />
      <span className="ml-2 text-muted">
        {u.facts} fact{u.facts === 1 ? "" : "s"}, {u.cited} cited
      </span>
    </li>
  );
  return (
    <section aria-label={title} className="flex flex-col gap-3 rounded-2xl border border-border bg-surface p-4">
      <div>
        <h2 className="text-sm font-medium">{title}</h2>
        <p className="text-xs text-muted">{hint}</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {collected
          ? [
              col("PDFs and papers", <FileText className="h-3.5 w-3.5" />, pdfs.map(collectedItem), pdfs.length),
              col("Web pages", <Globe className="h-3.5 w-3.5" />, pages.map(collectedItem), pages.length),
            ]
          : [
              col("PDFs and papers", <FileText className="h-3.5 w-3.5" />, usedPdfs.map(usedItem), usedPdfs.length),
              col("Web pages", <Globe className="h-3.5 w-3.5" />, usedPages.map(usedItem), usedPages.length),
            ]}
      </div>
      {!collected && usedOther.length > 0 ? (
        <div className="flex flex-col gap-2 border-t border-border pt-3">
          <h3 className="text-xs font-medium text-muted">Other documents ({usedOther.length})</h3>
          <ul className="flex flex-col gap-1.5 text-xs">{usedOther.map(usedItem)}</ul>
        </div>
      ) : null}
    </section>
  );
}

/** Live view of one deep-research run: where it is, what it has done, what it is doing now. Polls while active. */
export function RunView({ id }: { id: string }) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [error, setError] = useState("");
  const [stopping, setStopping] = useState(false);
  const [, setTick] = useState(0);
  const gone = useRef(false); // the run does not exist (404): stop asking

  const load = useCallback(async () => {
    try {
      const res = await fetch(`/api/runs/${encodeURIComponent(id)}`, { cache: "no-store" });
      if (res.status === 404) {
        gone.current = true;
        setError("This run was not found. It may have been started before runs were recorded.");
        return null;
      }
      if (!res.ok) throw new Error(`The server answered ${res.status}`);
      const body = (await res.json()) as RunDetail;
      setRun(body);
      setError("");
      return body;
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load this run");
      return null;
    }
  }, [id]);

  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const loop = async () => {
      const body = await load();
      if (!alive || gone.current) return;
      timer = setTimeout(loop, body && !isActive(body.status) ? 30000 : 3000);
    };
    loop();
    const clock = setInterval(() => setTick((n) => n + 1), 1000);
    return () => {
      alive = false;
      if (timer) clearTimeout(timer);
      clearInterval(clock);
    };
  }, [load]);

  const stop = async () => {
    if (stopping) return;
    setStopping(true);
    try {
      await fetch(`/api/runs/${encodeURIComponent(id)}/stop`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: "{}",
      });
      await load();
    } finally {
      setStopping(false);
    }
  };

  if (!run) {
    return error ? (
      <div role="alert" className="rounded-xl border border-warning/30 bg-warning-soft px-4 py-3 text-sm text-warning">
        {error}
      </div>
    ) : (
      <p className="text-sm text-muted">Loading run...</p>
    );
  }

  const active = isActive(run.status);
  const stage = run.status === "done" ? 7 : (STAGE_OF[run.step] ?? 0);
  const slug = reportSlug(run.reportPath);
  const p = run.progress;
  const elapsed = duration(run.startedAt, active ? new Date().toISOString() : run.updatedAt);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <RunBadge status={run.status} />
          {elapsed ? <span className="text-xs text-muted">{active ? "running for" : "took"} {elapsed}</span> : null}
          <span className="text-xs text-muted">· updated {ago(run.updatedAt)}</span>
        </div>
        <p className="whitespace-pre-wrap text-sm">{run.goal.split("\nClarifications from the user:")[0]}</p>
      </div>

      {run.note ? (
        <div role="status" className="flex items-start gap-2 rounded-xl border border-warning/30 bg-warning-soft px-4 py-3 text-sm text-warning">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          {run.note}
        </div>
      ) : null}
      {run.status === "failed" && run.error ? (
        <div role="alert" className="rounded-xl border border-warning/30 bg-warning-soft px-4 py-3 text-sm text-warning">
          <span className="font-medium">What went wrong: </span>
          {run.error}
        </div>
      ) : null}

      <ol className="flex flex-wrap items-center gap-x-2 gap-y-2" aria-label="Pipeline stages">
        {STAGES.map((name, i) => {
          const state = i < stage ? "done" : i === stage ? "current" : "todo";
          return (
            <li key={name} className="flex items-center gap-1.5 text-xs" aria-current={state === "current" ? "step" : undefined}>
              {state === "done" ? (
                <CheckCircle2 className="h-4 w-4 text-success" />
              ) : state === "current" ? (
                active && run.status !== "waiting" ? <Loader2 className="h-4 w-4 animate-spin text-accent" /> : <Circle className="h-4 w-4 fill-accent text-accent" />
              ) : (
                <Circle className="h-4 w-4 text-muted" />
              )}
              <span className={state === "todo" ? "text-muted" : "font-medium"}>{name}</span>
              {i < STAGES.length - 1 ? <span className="mx-1 text-muted">›</span> : null}
            </li>
          );
        })}
      </ol>

      {(p.questions_total || p.sections_total) ? (
        <div className="grid gap-4 sm:grid-cols-2">
          {p.questions_total ? <Bar label={`Questions answered (${p.evidence ?? 0} verified facts so far)`} done={p.questions_done ?? 0} total={p.questions_total} /> : null}
          {p.sections_total ? <Bar label="Report sections written" done={p.sections_done ?? 0} total={p.sections_total} /> : null}
        </div>
      ) : null}
      {active && p.current ? (
        <p className="text-sm text-muted">
          <span className="font-medium text-foreground">Now: </span>
          {p.current}
        </p>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        {run.status === "waiting" ? (
          <Link
            href={`/deep?thread=${encodeURIComponent(run.id)}`}
            className="rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-accent-foreground shadow-sm shadow-accent/30"
          >
            Open to {run.waitingFor === "clarify" ? "answer the questions" : run.waitingFor === "review" ? "choose sources" : "review the plan"}
          </Link>
        ) : null}
        {slug ? (
          <Link href={`/research/${slug}`} className="rounded-full bg-success px-5 py-2.5 text-sm font-medium text-white">
            Open the report
          </Link>
        ) : null}
        {active ? (
          <button
            type="button"
            onClick={stop}
            disabled={stopping}
            className="flex items-center gap-1.5 rounded-full border border-border px-4 py-2 text-sm font-medium hover:border-accent/40 disabled:opacity-50"
          >
            <Square className="h-3.5 w-3.5" />
            {stopping ? "Stopping..." : "Stop this run"}
          </button>
        ) : null}
        {!active && run.status !== "done" ? (
          <Link
            href={`/deep?goal=${encodeURIComponent(run.goal.split("\nClarifications from the user:")[0].slice(0, 4000))}`}
            className="flex items-center gap-1.5 rounded-full border border-border px-4 py-2 text-sm font-medium hover:border-accent/40"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Start this goal again
          </Link>
        ) : null}
      </div>

      {run.collected.length > 0 ? (
        <SourceColumns
          title="Collected for this run"
          hint="What the collector fetched after you chose sources. Saved ones are now in your library; the others are listed with the reason they were left out."
          collected={run.collected}
        />
      ) : null}
      {run.sources.length > 0 ? (
        <SourceColumns
          title="Used in the report"
          hint="The documents the report's evidence came from, with how many facts each supplied and how many the report cites."
          used={run.sources}
        />
      ) : null}

      <section aria-label="Activity">
        <h2 className="mb-2 text-sm font-medium">Activity</h2>
        {run.events.length === 0 ? (
          <p className="text-sm text-muted">Nothing recorded yet.</p>
        ) : (
          <ul className="flex max-h-[28rem] flex-col gap-1 overflow-y-auto rounded-2xl border border-border bg-surface p-3 text-xs">
            {[...run.events].reverse().map((e, i) => (
              <li key={`${e.t}-${i}`} className="flex gap-3">
                <time className="shrink-0 tabular-nums text-muted" dateTime={e.t}>
                  {new Date(e.t).toLocaleTimeString()}
                </time>
                <span className={e.level === "error" ? "text-warning" : ""}>{e.text}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {!run.backendReachable ? <p className="text-xs text-muted">The research backend is not answering; showing the last recorded state.</p> : null}
      {error ? <p className="text-xs text-warning">{error}</p> : null}
    </div>
  );
}
