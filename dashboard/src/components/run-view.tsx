"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import type { CollectedRow, RunDetail, UsedSource } from "@/lib/runs";
import { safeHref } from "@/lib/safe-href";
import { RunBadge, ago, duration, isActive } from "@/components/run-status";
import { ErrorCard } from "@/components/error-card";

// The pipeline as the user thinks of it. Each backend step belongs to one stage.
const STAGES = ["Library", "Questions", "Plan", "Sources", "Evidence", "Writing", "Saved"] as const;
const STAGE_OF: Record<string, number> = {
  library: 0, questions: 1, clarify: 1, plan: 2, approve: 2, discover: 3, review: 3, collect: 3, research: 4, write: 5, save: 6, done: 7,
};

function reportSlug(path: string): string | null {
  const file = path.split(/[\\/]/).pop();
  return file ? file.replace(/\.md$/, "") : null;
}

const isPdf = (kind: string) => kind === "pdf" || kind === "paper";
const btn = "rounded px-4 py-2.5 text-sm font-semibold";
const primary = `${btn} bg-accent text-accent-foreground hover:opacity-90`;
const ghost = `${btn} border border-foreground hover:bg-foreground hover:text-background`;
const danger = `${btn} border border-danger text-danger hover:bg-danger hover:text-accent-foreground disabled:opacity-50`;

function SourceRow({ title, url, trailing, tone }: { title: string; url: string; trailing: string; tone?: string }) {
  return (
    <div className="py-1 text-[13.5px] leading-snug">
      {url ? (
        <a href={safeHref(url)} target="_blank" rel="noopener noreferrer nofollow" className="hover:text-accent hover:underline">
          {title}
        </a>
      ) : (
        <span>{title}</span>
      )}{" "}
      <span className={tone ?? "text-muted"}>{trailing}</span>
    </div>
  );
}

/** "Collected for this run" (what the collector fetched) or "Used in the report", with PDFs and web pages apart. */
function Sources({ run }: { run: RunDetail }) {
  const collected: CollectedRow[] = run.collected;
  const used: UsedSource[] = run.sources;
  const showCollected = collected.length > 0;
  const pdfs = showCollected ? collected.filter((c) => isPdf(c.kind)) : used.filter((u) => isPdf(u.kind));
  const webs = showCollected ? collected.filter((c) => !isPdf(c.kind)) : used.filter((u) => !isPdf(u.kind));
  const row = (x: CollectedRow | UsedSource, i: number) =>
    "status" in x ? (
      <SourceRow key={`${x.url}-${i}`} title={x.title || x.url} url={x.url} trailing={x.status === "saved" ? "saved" : `${x.status}${x.reason ? `: ${x.reason}` : ""}`} tone={x.status === "saved" ? "text-success" : "text-warning"} />
    ) : (
      <SourceRow key={`${x.url}-${x.title}-${i}`} title={x.title} url={x.url} trailing={`${x.facts} fact${x.facts === 1 ? "" : "s"}, ${x.cited} cited`} />
    );
  return (
    <div className="border border-border border-t-[3px] border-t-foreground bg-surface p-5">
      <div className="font-serif text-2xl">{showCollected ? "Collected for this run" : "Used in the report"}</div>
      <p className="mb-3 mt-1 text-xs text-muted">
        {showCollected
          ? "What the collector fetched after you chose sources. Saved ones are now in your library; the others say why they were left out."
          : "The documents the report's evidence came from, with how many facts each supplied."}
      </p>
      <div className="text-xs font-semibold text-info">PDFs and papers · {pdfs.length}</div>
      {pdfs.length ? pdfs.map(row) : <div className="py-1 text-sm text-muted">None</div>}
      <div className="mt-4 text-xs font-semibold text-success">Web pages · {webs.length}</div>
      {webs.length ? webs.map(row) : <div className="py-1 text-sm text-muted">None</div>}
    </div>
  );
}

/** Live view of one deep-research run: where it is, what it has done, what it is doing now. Polls while active. */
export function RunView({ id, onChanged }: { id: string; onChanged?: () => void }) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [error, setError] = useState("");
  const [stopping, setStopping] = useState(false);
  const [confirm, setConfirm] = useState(false);
  const [, setTick] = useState(0);
  const gone = useRef(false); // the run does not exist (404): stop asking

  const load = useCallback(async () => {
    try {
      const res = await fetch(`/api/runs/${encodeURIComponent(id)}`, { cache: "no-store" });
      if (res.status === 404) {
        gone.current = true;
        setError("This run was not found. It may have been archived.");
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
    gone.current = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- switching runs clears the old one
    setRun(null);
    setConfirm(false);
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
      await fetch(`/api/runs/${encodeURIComponent(id)}/stop`, { method: "POST", headers: { "content-type": "application/json" }, body: "{}" });
      setConfirm(false);
      await load();
      onChanged?.();
    } finally {
      setStopping(false);
    }
  };

  if (!run) {
    return error ? (
      /not found/i.test(error) ? (
        <p className="font-serif text-2xl italic text-muted">{error}</p>
      ) : (
        <ErrorCard error={error} onRetry={() => void load()} context="this run" />
      )
    ) : (
      <p className="text-sm text-muted">Loading run...</p>
    );
  }

  const active = isActive(run.status);
  const stage = run.status === "done" ? 7 : (STAGE_OF[run.step] ?? 0);
  const slug = reportSlug(run.reportPath);
  const p = run.progress;
  const elapsed = duration(run.startedAt, active ? new Date().toISOString() : run.updatedAt);
  const goal = run.goal.split("\nClarifications from the user:")[0];
  // the plan is known long before the research counters start, so the cards use it until they do
  const questionsTotal = p.questions_total || run.plan?.questions.length || 0;
  const sectionsTotal = p.sections_total || run.plan?.outline.length || 0;

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <RunBadge status={run.status} />
        <span className="text-[13px] text-muted">
          started {ago(run.startedAt)}
          {elapsed ? ` · ${active ? "running for" : "took"} ${elapsed}` : ""}
        </span>
        <div className="flex-1" />
        {active && (
          <button type="button" onClick={() => setConfirm(true)} className={danger}>
            Stop this run
          </button>
        )}
        {run.status === "waiting" && (
          <Link href={`/deep?thread=${encodeURIComponent(run.id)}`} className={primary}>
            Open to {run.waitingFor === "clarify" ? "answer the questions" : run.waitingFor === "review" ? "choose sources" : "review the plan"}
          </Link>
        )}
        {slug && (
          <Link href={`/research/${slug}`} className={primary}>
            Open the report
          </Link>
        )}
        {!active && run.status !== "done" && (
          <Link href={`/deep?goal=${encodeURIComponent(goal.slice(0, 4000))}`} className={ghost}>
            Start this goal again
          </Link>
        )}
        {run.status === "done" && (
          <Link
            href={`/deep?goal=${encodeURIComponent(goal.slice(0, 4000))}`}
            title="Starts a new run. The sources this run collected stay in your library, so it only gathers what is still missing."
            className={ghost}
          >
            Continue researching this
          </Link>
        )}
      </div>

      <h2 className="whitespace-pre-wrap text-4xl leading-tight">{goal}</h2>

      {confirm && (
        <div className="border border-danger p-4 text-sm leading-relaxed">
          <b>Stop this run?</b> It stops within seconds, even in the middle of a model call. Facts found so far are kept.
          <div className="mt-3 flex gap-2">
            <button type="button" onClick={stop} disabled={stopping} className={danger}>
              {stopping ? "Stopping..." : "Stop run"}
            </button>
            <button type="button" onClick={() => setConfirm(false)} className={ghost}>
              Keep running
            </button>
          </div>
        </div>
      )}
      {run.note && (
        <div role="status" className="border border-warning bg-warning-soft px-4 py-3 text-sm text-warning">
          {run.note}
        </div>
      )}
      {run.status === "failed" && run.error && (
        <div role="alert" className="border border-danger px-4 py-3 text-sm leading-relaxed">
          <b>What went wrong:</b> {run.error}
        </div>
      )}

      <ol className="flex flex-wrap gap-2" aria-label="Pipeline stages">
        {STAGES.map((name, i) => {
          const state = i < stage ? "done" : i === stage ? "current" : "todo";
          return (
            <li
              key={name}
              aria-current={state === "current" ? "step" : undefined}
              className={`rounded border px-3 py-1.5 text-[13px] ${
                state === "done" ? "border-success text-success" : state === "current" ? "border-accent font-semibold text-accent" : "border-border text-muted"
              }`}
            >
              {name}
            </li>
          );
        })}
      </ol>
      {active && p.current && (
        <p className="text-sm text-muted">
          <span className="font-semibold text-foreground">Now: </span>
          {p.current}
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          { label: "Questions", value: questionsTotal ? `${p.questions_done ?? 0} of ${questionsTotal}` : "—", hint: questionsTotal ? "answered so far" : "no plan yet" },
          { label: "Verified facts", value: String(p.evidence ?? 0), hint: "kept as evidence" },
          { label: "Sections", value: sectionsTotal ? `${p.sections_done ?? 0} of ${sectionsTotal}` : "—", hint: sectionsTotal ? "chapters written so far" : "no plan yet" },
        ].map((s) => (
          <div key={s.label} className="border border-border border-t-[3px] border-t-foreground bg-surface px-5 py-4">
            <div className="text-[13px] text-muted">{s.label}</div>
            <div className="font-serif text-5xl leading-tight">{s.value}</div>
            <div className="text-xs text-muted">{s.hint}</div>
          </div>
        ))}
      </div>

      {(run.clarifyQuestions.length > 0 || (run.plan && run.plan.questions.length > 0)) && (
        <div className="grid gap-5 xl:grid-cols-2">
          {run.clarifyQuestions.length > 0 && (
            <section aria-label="Questions and answers" className="border border-border border-t-[3px] border-t-foreground bg-surface p-5">
              <div className="font-serif text-2xl">Questions it asked you</div>
              <p className="mb-3 mt-1 text-xs text-muted">
                {run.status === "waiting" && run.waitingFor === "clarify" ? "Waiting for your answers." : "What it asked before planning, and what you said. Your answers shaped the plan."}
              </p>
              {run.clarifyQuestions.map((q, i) => {
                const a = run.clarifications.find((p) => p.question === q)?.answer ?? "";
                const waitingHere = run.status === "waiting" && run.waitingFor === "clarify";
                return (
                  <div key={q} className="border-t border-border py-3">
                    <div className="flex gap-3">
                      <span className="font-serif text-2xl leading-none text-muted">{i + 1}</span>
                      <div className="min-w-0 flex-1">
                        <div className="font-serif text-lg leading-snug">{q}</div>
                        {waitingHere ? (
                          <div className="mt-1 text-sm italic text-muted">Not answered yet.</div>
                        ) : a ? (
                          <div className="mt-1.5 border-l-[3px] border-accent pl-3 text-[15px] leading-relaxed">{a}</div>
                        ) : (
                          <div className="mt-1 text-sm italic text-muted">You left this to the assistant.</div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </section>
          )}
          {run.plan && run.plan.questions.length > 0 && (
            <section aria-label="Plan questions" className="border border-border border-t-[3px] border-t-foreground bg-surface p-5">
              <div className="font-serif text-2xl">{run.plan.title || "The questions it is answering"}</div>
              <p className="mb-3 mt-1 text-xs text-muted">What your library already knew about each question, and what was found.</p>
              {run.plan.questions.map((q, i) => {
                const cov = run.coverage.find((c) => c.index === i);
                const done = i < (p.questions_done ?? 0);
                const now = !done && run.status === "running" && i === (p.questions_done ?? 0) && stage === 4;
                const facts = run.questionFacts[i];
                const tone = cov?.status === "answered" ? "text-success" : cov?.status === "thin" ? "text-warning" : cov ? "text-danger" : "";
                return (
                  <div key={q} className="flex gap-3 border-t border-border py-3">
                    <span className="font-serif text-2xl leading-none text-muted">{i + 1}</span>
                    <div className="min-w-0 flex-1">
                      <div className="font-serif text-lg leading-snug">{q}</div>
                      <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5 text-[13px]">
                        {cov && <span className={tone}>{cov.status === "answered" ? `library covered it (${cov.relevant} documents)` : cov.status === "thin" ? "library had one document" : "nothing in the library"}</span>}
                        {done ? <span className="font-semibold text-success">answered{typeof facts === "number" ? ` · ${facts} fact${facts === 1 ? "" : "s"}` : ""}</span> : now ? <span className="font-semibold text-accent">working on it now</span> : <span className="text-muted">waiting its turn</span>}
                      </div>
                    </div>
                  </div>
                );
              })}
              {run.plan.outline.length > 0 && (
                <div className="mt-3 border-t border-border pt-3 text-sm">
                  <div className="text-[11px] font-semibold uppercase tracking-widest text-muted">Chapters</div>
                  <div className="mt-1 leading-relaxed">{run.plan.outline.map((t, i) => `${["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"][i] ?? i + 1}. ${t}`).join("  ·  ")}</div>
                </div>
              )}
            </section>
          )}
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-2">
        <section aria-label="Activity" className="border border-border border-t-[3px] border-t-foreground bg-surface p-5">
          <div className="mb-3 font-serif text-2xl">Newswire</div>
          {run.events.length === 0 ? (
            <p className="text-sm text-muted">Nothing recorded yet.</p>
          ) : (
            <ul className="flex max-h-[26rem] flex-col gap-1.5 overflow-y-auto text-[13.5px] leading-snug">
              {[...run.events].reverse().map((e, i) => (
                <li key={`${e.t}-${i}`} className="flex gap-3">
                  <time className="shrink-0 tabular-nums text-muted" dateTime={e.t}>
                    {new Date(e.t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </time>
                  <span className={e.level === "error" ? "text-warning" : ""}>{e.text}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
        {run.collected.length > 0 || run.sources.length > 0 ? (
          <Sources run={run} />
        ) : (
          <div className="border border-border border-t-[3px] border-t-foreground bg-surface p-5">
            <div className="font-serif text-2xl">Collected for this run</div>
            <p className="mt-2 text-sm text-muted">Nothing collected yet. Sources appear here once you choose what to keep.</p>
          </div>
        )}
      </div>

      {!run.backendReachable && <p className="text-xs text-muted">The research backend is not answering; showing the last recorded state.</p>}
      {error && <p className="text-xs text-warning">{error}</p>}
    </div>
  );
}
