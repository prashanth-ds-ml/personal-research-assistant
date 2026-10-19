"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useStream } from "@langchain/langgraph-sdk/react";
import { ResumeBanner } from "@/components/resume-banner";
import { ErrorCard } from "@/components/error-card";
import { DeskCards } from "@/components/desk-cards";
import { useRunThread } from "@/lib/use-run-thread";
import { apiUrl } from "@/lib/api-url";
import { safeHref } from "@/lib/safe-href";
import type { RunDetail } from "@/lib/runs";
import { ago } from "@/components/run-status";

// State shape of the `deep_research` graph (src/research_assistant/goal_graph.py).
interface Plan {
  title: string;
  sub_questions: string[];
  outline: { title: string; questions: number[]; brief?: string; synthesis?: boolean }[];
}
interface DeepState {
  goal?: string;
  refined_goal?: string;
  plan?: Plan;
  evidence?: unknown[];
  report?: string;
  report_path?: string;
  stats?: { questions: number; sections: number; evidence: number; words: number };
  collect_report?: { saved?: number; pages?: number; papers?: number; skipped?: number; failed?: number; folder?: string; error?: string };
  library_update?: { added?: number; removed?: number; documents?: number; failed?: string[]; error?: string };
}
type ClarifyInterrupt = { type: "clarify"; goal: string; questions: string[] };
interface CoverageRow {
  index: number;
  question: string;
  status: "answered" | "thin" | "nothing";
  relevant: number;
  checked: number;
  titles: string[];
}
type ApproveInterrupt = { type: "approve_plan"; plan: Plan; revisions_left: number; coverage?: CoverageRow[] };
interface ReviewCandidate {
  id: string;
  title: string;
  url: string;
  site: string;
  kind: "page" | "paper";
  question: string;
  question_index: number;
  score: number;
  snippet: string;
}
type ReviewInterrupt = {
  type: "review_sources";
  candidates: ReviewCandidate[];
  max_sources: number;
  min_relevance: number;
  error?: string;
};
type DeepInterrupt = ClarifyInterrupt | ApproveInterrupt | ReviewInterrupt;

function reportSlug(reportPath?: string): string | null {
  const file = reportPath?.split(/[\\/]/).pop();
  return file ? file.replace(/\.md$/, "") : null;
}

const STEPS = ["Brief", "Questions", "Plan", "Sources", "Progress", "Report"] as const;
const STAGES = ["Library", "Questions", "Plan", "Sources", "Evidence", "Writing", "Saved"] as const;
const STAGE_OF: Record<string, number> = {
  library: 0, questions: 1, clarify: 1, plan: 2, approve: 2, discover: 3, review: 3, collect: 3, research: 4, write: 5, save: 6, done: 7,
};

const paper = "border border-border bg-surface";
const btn = "rounded px-6 py-3 text-[15px] font-semibold disabled:cursor-not-allowed disabled:opacity-40";
const primary = `${btn} bg-accent text-accent-foreground hover:opacity-90`;
const ghost = `${btn} border border-foreground hover:bg-foreground hover:text-background`;
const danger = `${btn} border border-danger text-danger hover:bg-danger hover:text-accent-foreground`;
const link = "text-sm font-semibold text-accent hover:underline";

const STARTERS = ["Compare two retrieval methods", "Should we fine-tune or prompt?", "State of tool calling in small models"];

function DeepResearchForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // "Start this goal again" and the search box arrive with the goal in the address.
  const [goal, setGoal] = useState(() => searchParams.get("goal") ?? "");
  const [answers, setAnswers] = useState<string[]>([]);
  const [qIdx, setQIdx] = useState(0);
  const [feedback, setFeedback] = useState("");
  const [askChanges, setAskChanges] = useState(false);
  const [collectChoice, setCollectChoice] = useState<"gaps" | "all" | "none" | null>(null);
  const [seeds, setSeeds] = useState("");
  const [showSeeds, setShowSeeds] = useState(false);
  const [archived, setArchived] = useState(false);
  const [openRow, setOpenRow] = useState<number | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [confirmStop, setConfirmStop] = useState(false);
  const [detail, setDetail] = useState<RunDetail | null>(null);

  // Remember the run's thread so leaving this page does not cancel it (see use-run-thread.ts).
  const { threadId, remember, forget } = useRunThread("deep-research-thread");
  const stream = useStream<DeepState>({
    apiUrl: apiUrl(),
    assistantId: "deep_research",
    threadId,
    onThreadId: remember,
    reconnectOnMount: () => window.localStorage, // same storage the thread id lives in
  });
  const active = Boolean(threadId);

  // "Open to answer" on the Runs page arrives with ?thread=<run id>: remember it, then tidy the address.
  const wantedThread = searchParams.get("thread");
  useEffect(() => {
    if (wantedThread) {
      remember(wantedThread);
      router.replace("/deep");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only on arrival
  }, []);
  const keepAlive = { onDisconnect: "continue", streamResumable: true } as const;

  const startOver = () => {
    forget();
    setGoal("");
    setAnswers([]);
    setQIdx(0);
    setFeedback("");
    setAskChanges(false);
    setSeeds("");
    setShowSeeds(false);
    setCollectChoice(null);
    setOpenRow(null);
    setDetail(null);
  };

  // The graph pauses (LangGraph `interrupt`) to ask questions / show the plan.
  // Only our own three interrupt shapes are acted on (LangGraph can also report a `{when: "breakpoint"}` pause).
  const raw = (stream.interrupt?.value ?? null) as { type?: string } | null;
  const pending =
    raw && (raw.type === "clarify" || raw.type === "approve_plan" || raw.type === "review_sources")
      ? (raw as DeepInterrupt)
      : null;

  // Which candidate sources are ticked. Defaults come from the relevance score; the user's clicks override them.
  const reviewKey = pending?.type === "review_sources" ? pending.candidates.map((c) => c.id).join("|") : "";
  const [overrides, setOverrides] = useState<{ key: string; map: Record<string, boolean> }>({ key: "", map: {} });
  const ticks = overrides.key === reviewKey ? overrides.map : {};
  const isTicked = (c: ReviewCandidate, min: number) => ticks[c.id] ?? c.score >= min;
  const setTick = (id: string, value: boolean) => setOverrides({ key: reviewKey, map: { ...ticks, [id]: value } });
  const gaps = pending?.type === "approve_plan" ? (pending.coverage ?? []).filter((r) => r.status !== "answered") : [];
  const effectiveCollect: "gaps" | "all" | "none" = collectChoice ?? (gaps.length > 0 ? "gaps" : "none");
  const slug = reportSlug(stream.values.report_path);
  const started = stream.isLoading || Boolean(stream.values.goal) || Boolean(pending);

  // A remembered thread the server no longer has would leave the page stuck on an error: drop it so the form returns.
  useEffect(() => {
    if (threadId && stream.error && !stream.isLoading && !stream.values.goal && /404|not found/i.test(String(stream.error))) {
      forget();
    }
  }, [threadId, stream.error, stream.isLoading, stream.values.goal, forget]);

  // While the run works, read its record (stage, counts, newswire) the same way the Runs screen does.
  const working = Boolean(threadId) && started && !pending && !slug;
  const loadDetail = useCallback(async () => {
    if (!threadId) return;
    try {
      const r = await fetch(`/api/runs/${encodeURIComponent(threadId)}`, { cache: "no-store" });
      if (r.ok) setDetail((await r.json()) as RunDetail);
    } catch {
      /* the next tick will try again */
    }
  }, [threadId]);
  useEffect(() => {
    if (!working) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- first read, then poll
    void loadDetail();
    const t = setInterval(loadDetail, 4000);
    return () => clearInterval(t);
  }, [working, loadDetail]);

  const resume = (value: unknown) => {
    if (stream.isLoading) return; // a double click must not resume the same pause twice
    stream.submit(undefined, { command: { resume: value }, ...keepAlive });
  };

  const start = () => {
    if (!goal.trim() || stream.isLoading) return;
    setAnswers([]);
    setQIdx(0);
    setFeedback("");
    stream.submit(
      { goal },
      { config: { configurable: { seed_urls: seeds, include_archived_pages: archived } }, ...keepAlive }
    );
  };

  const sendAnswers = (questions: string[], skip = false) => {
    const text = skip
      ? ""
      : questions
          .map((q, i) => (answers[i]?.trim() ? `${q}\n  -> ${answers[i].trim()}` : ""))
          .filter(Boolean)
          .join("\n");
    setAnswers([]);
    setQIdx(0);
    resume(text);
  };

  const stopRun = async () => {
    if (!threadId) return;
    try {
      await fetch(`/api/runs/${encodeURIComponent(threadId)}/stop`, { method: "POST", headers: { "content-type": "application/json" }, body: "{}" });
    } finally {
      setConfirmStop(false);
      void loadDetail();
    }
  };

  const cur = slug ? 5 : pending?.type === "clarify" ? 1 : pending?.type === "approve_plan" ? 2 : pending?.type === "review_sources" ? 3 : started || active ? 4 : 0;
  const busy = stream.isLoading;

  return (
    <div className="-mx-6 -my-8 sm:-my-10 lg:-mx-14">
      {/* the six chapters of the journey */}
      <ol aria-label="Progress through the research" className="flex flex-wrap border-b border-border bg-surface px-6 lg:px-14">
        {STEPS.map((s, i) => (
          <li
            key={s}
            aria-current={i === cur ? "step" : undefined}
            className={`mr-3 border-b-[3px] py-4 pr-6 text-[15px] font-medium ${i === cur ? "border-accent text-foreground" : "border-transparent text-muted"}`}
          >
            <span className="font-serif text-[22px] font-medium">{i + 1}</span>&nbsp; {s}
          </li>
        ))}
      </ol>

      <div className="mx-auto max-w-[1680px] px-6 py-10 lg:px-14">
        {active && (
          <div className="mb-5">
            <ResumeBanner loading={busy} waiting={Boolean(pending)} noun="goal" onReset={startOver} />
          </div>
        )}

        {stream.error ? (
          <div className="mb-6">
            <ErrorCard error={stream.error} />
          </div>
        ) : null}

        {stream.values.library_update?.documents !== undefined && (
          <div className="mb-3 text-xs text-muted">
            Library: {stream.values.library_update.documents} documents
            {stream.values.library_update.added ? `, ${stream.values.library_update.added} new indexed for this run` : ""}
            {stream.values.library_update.failed?.length ? `, ${stream.values.library_update.failed.length} could not be read` : ""}
          </div>
        )}
        {stream.values.collect_report && !stream.values.collect_report.error && (
          <div className="mb-3 text-xs text-muted">
            Collected sources: {stream.values.collect_report.saved ?? 0} added to your library
            {stream.values.collect_report.pages !== undefined ? ` (${stream.values.collect_report.pages} web pages, ${stream.values.collect_report.papers ?? 0} papers)` : ""},{" "}
            {stream.values.collect_report.skipped ?? 0} skipped{stream.values.collect_report.failed ? `, ${stream.values.collect_report.failed} failed` : ""}
          </div>
        )}
        {stream.values.collect_report?.error && (
          <div className="mb-3 text-xs text-warning">Could not fetch new sources ({stream.values.collect_report.error}); researching your existing library.</div>
        )}
        {stream.values.library_update?.error && (
          <div className="mb-3 text-xs text-warning">Could not update the library ({stream.values.library_update.error}); using the existing index.</div>
        )}

        <div className="mb-2" />

        {/* 1. BRIEF */}
        {cur === 0 && (
          <div className="grid gap-12 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <div>
              <div className="kicker">New assignment</div>
              <h1 className="my-3 text-5xl leading-[1.02] tracking-tight sm:text-7xl">
                What shall we
                <br />
                look into?
              </h1>
              <label htmlFor="goal" className="mb-2 mt-6 block text-sm text-muted">
                Write it as you would brief a colleague.
              </label>
              <textarea
                id="goal"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                disabled={busy}
                placeholder="e.g. Should our team adopt hybrid retrieval for the clinical guideline search? Cover accuracy, failure modes and cost."
                className="h-32 w-full resize-none border-0 border-b-2 border-foreground bg-transparent py-1.5 font-serif text-2xl leading-snug outline-none placeholder:text-muted focus:border-accent"
              />
              {showSeeds && (
                <div className="mt-5">
                  <label htmlFor="seeds" className="mb-1 block text-[11px] font-semibold uppercase tracking-widest text-muted">
                    Pages or PDFs to add first (one address per line)
                  </label>
                  <textarea
                    id="seeds"
                    value={seeds}
                    onChange={(e) => setSeeds(e.target.value)}
                    placeholder="https://example.org/a-useful-article"
                    className="h-20 w-full resize-none rounded border border-border bg-surface p-3 text-sm outline-none focus:border-accent"
                  />
                  <p className="mt-1 text-xs text-muted">They are fetched after you approve the plan, with robots.txt respected.</p>
                </div>
              )}
              <div className="mt-6 flex flex-wrap items-center gap-x-5 gap-y-3">
                <button type="button" onClick={start} disabled={busy || !goal.trim()} className={primary}>
                  {busy ? "Working..." : "Begin research →"}
                </button>
                <button type="button" onClick={() => setShowSeeds((v) => !v)} className={link}>
                  + Add pages or PDFs first
                </button>
                <label className="flex cursor-pointer items-center gap-2 text-sm font-semibold text-accent">
                  <input type="checkbox" checked={archived} onChange={(e) => setArchived(e.target.checked)} className="h-4 w-4 accent-accent" />
                  Include archived pages
                </label>
                <span className="text-sm text-muted">Plan 30 to 60 minutes on this machine</span>
              </div>
              <div className="mt-10 text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">Or start from</div>
              <div className="mt-3 flex flex-wrap gap-2.5">
                {STARTERS.map((s) => (
                  <button key={s} type="button" onClick={() => setGoal(s)} className={`${paper} rounded px-4 py-2.5 text-sm hover:border-accent`}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
            <DeskCards onAnswer={(id) => remember(id)} />
          </div>
        )}

        {/* 2. QUESTIONS */}
        {pending?.type === "clarify" && (() => {
          const qs = pending.questions;
          const i = Math.min(qIdx, qs.length - 1);
          const last = i === qs.length - 1;
          return (
            <div className="grid gap-12 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
              <div className="max-w-3xl">
                <div className="kicker">
                  Question {i + 1} of {qs.length}
                </div>
                <h2 className={`my-3 leading-[1.12] tracking-tight ${qs[i].length > 90 ? "text-3xl sm:text-4xl" : "text-4xl sm:text-5xl"}`}>{qs[i]}</h2>
                <label htmlFor="answer" className="text-sm text-muted">
                  Your answer, or leave it blank and I will decide.
                </label>
                <textarea
                  id="answer"
                  value={answers[i] ?? ""}
                  onChange={(e) => setAnswers((a) => Object.assign([...a], { [i]: e.target.value }))}
                  className="mt-2 h-28 w-full resize-none rounded border-[1.5px] border-foreground bg-surface p-3.5 text-lg outline-none focus:border-accent"
                />
                <div className="mt-5 flex flex-wrap items-center gap-3">
                  <button type="button" onClick={() => setQIdx(Math.max(0, i - 1))} disabled={i === 0} className={ghost}>
                    Back
                  </button>
                  <button type="button" onClick={() => (last ? sendAnswers(qs) : setQIdx(i + 1))} disabled={busy} className={primary}>
                    {last ? "Finish questions →" : "Next question →"}
                  </button>
                  <button type="button" onClick={() => sendAnswers(qs, true)} disabled={busy} className={`${btn} border border-border text-muted`}>
                    Skip all
                  </button>
                </div>
                <div className="mt-7 flex gap-2">
                  {qs.map((q, n) => (
                    <span key={q} className={`h-1 w-9 rounded-sm ${n <= i ? "bg-accent" : "bg-border"}`} />
                  ))}
                </div>
              </div>
              <div className={`${paper} h-fit border-l-4 border-l-accent p-6`}>
                <div className="mb-2 text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">Why I ask</div>
                <p className="font-serif text-xl italic leading-relaxed text-muted">
                  Your answer changes which documents are worth reading first and how the plan is split. Leave it blank and I choose sensible defaults.
                </p>
              </div>
            </div>
          );
        })()}

        {/* 3. PLAN */}
        {pending?.type === "approve_plan" && (() => {
          const cov = pending.coverage ?? [];
          const n = (s: string) => cov.filter((r) => r.status === s).length;
          const tone = { answered: "text-success", thin: "text-warning", nothing: "text-danger" } as const;
          const bar = { answered: "bg-success", thin: "bg-warning", nothing: "bg-danger" } as const;
          return (
            <div className="grid gap-12 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
              <div>
                <div className="kicker">The brief</div>
                <h2 className="my-2 text-5xl leading-[1.1] tracking-tight">
                  {pending.plan.sub_questions.length} questions, and what your library already knows about each
                </h2>
                {cov.length > 0 && (
                  <div className="my-4 flex flex-wrap items-center gap-4 text-sm">
                    <span className="rounded bg-success-soft px-2.5 py-1 text-xs font-semibold uppercase tracking-wider text-success">{n("answered")} covered</span>
                    <span className="rounded bg-warning-soft px-2.5 py-1 text-xs font-semibold uppercase tracking-wider text-warning">{n("thin")} thin</span>
                    <span className="rounded bg-danger-soft px-2.5 py-1 text-xs font-semibold uppercase tracking-wider text-danger">{n("nothing")} nothing</span>
                    <span className="text-muted">click a question for the documents behind it</span>
                  </div>
                )}
                {gaps.length > 0 && cov.length > 0 && gaps.length * 2 >= cov.length && (
                  <p role="status" className="mb-3 border border-warning bg-warning-soft px-4 py-3 text-sm text-warning">
                    {gaps.length} of {cov.length} questions are not well covered by your library. With this little material the report would mostly say what is missing: collecting sources first is strongly advised.
                  </p>
                )}
                {pending.plan.sub_questions.map((q, i) => {
                  const row = cov.find((r) => r.index === i);
                  const open = openRow === i;
                  return (
                    <div key={q} className="border-t border-border">
                      <button type="button" onClick={() => setOpenRow(open ? null : i)} className="grid w-full grid-cols-[44px_minmax(0,1fr)_190px] items-center gap-3 py-3.5 text-left">
                        <span className="font-serif text-3xl text-muted">{i + 1}</span>
                        <span className="font-serif text-xl leading-snug">{q}</span>
                        <span>
                          {row ? (
                            <>
                              <span className="block h-2 rounded-sm bg-border">
                                <span className={`block h-2 rounded-sm ${bar[row.status]}`} style={{ width: row.status === "answered" ? "90%" : row.status === "thin" ? "35%" : "3%" }} />
                              </span>
                              <span className={`mt-1.5 block text-xs ${tone[row.status]}`}>
                                {row.status === "answered" ? `covered (${row.relevant} documents)` : row.status === "thin" ? "thin: one document" : "nothing in the library"}
                              </span>
                            </>
                          ) : null}
                        </span>
                      </button>
                      {open && row && (
                        <div className="mb-3 ml-[56px] border-l-[3px] border-border pl-4 text-sm">
                          {row.titles.length > 0 ? (
                            <>
                              <div className="mb-1 text-xs font-semibold uppercase tracking-widest text-muted">Documents behind it</div>
                              {row.titles.map((t) => (
                                <div key={t} className="py-0.5">
                                  {t}
                                </div>
                              ))}
                            </>
                          ) : (
                            <p className="text-muted">The library has nothing relevant for this question. Collect sources for it below.</p>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
              <div className="flex h-fit flex-col gap-5">
                <fieldset className={`${paper} p-6`} disabled={busy}>
                  <legend className="sr-only">Collect new sources before researching?</legend>
                  <div className="mb-3 text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">Gather new reading first?</div>
                  {(
                    [
                      { value: "gaps", label: `Yes, for the ${gaps.length} question${gaps.length === 1 ? "" : "s"} the library covers poorly`, off: gaps.length === 0 },
                      { value: "all", label: "Yes, for every question", off: false },
                      { value: "none", label: "No, use the library as it is", off: false },
                    ] as const
                  ).map((o) => (
                    <label key={o.value} className={`flex cursor-pointer items-start gap-2.5 py-2.5 text-[15px] leading-snug ${o.off ? "opacity-50" : ""}`}>
                      <input type="radio" name="collect" className="mt-1 h-4 w-4 accent-accent" checked={effectiveCollect === o.value} disabled={o.off} onChange={() => setCollectChoice(o.value)} />
                      {o.label}
                    </label>
                  ))}
                  <p className="mt-1.5 text-[13px] leading-relaxed text-muted">You will see everything found, papers apart from web pages, before anything is saved.</p>
                </fieldset>
                <div className={`${paper} p-6`}>
                  <div className="mb-2 text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">Chapters of the report</div>
                  <ol className="font-serif text-lg leading-[1.8]">
                    {pending.plan.outline.map((s, i) => (
                      <li key={s.title} className={s.synthesis ? "italic text-muted" : ""}>
                        {["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"][i] ?? i + 1}. {s.title}
                      </li>
                    ))}
                  </ol>
                </div>
                {askChanges && pending.revisions_left > 0 && (
                  <div className={`${paper} p-5`}>
                    <label htmlFor="fb" className="mb-1 block text-xs text-muted">
                      {pending.revisions_left} revision{pending.revisions_left === 1 ? "" : "s"} left. The coverage check runs again on the new plan.
                    </label>
                    <input
                      id="fb"
                      value={feedback}
                      onChange={(e) => setFeedback(e.target.value)}
                      placeholder="e.g. add a section on cost, drop the history of RAG"
                      className="w-full rounded border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent"
                    />
                    <button
                      type="button"
                      disabled={!feedback.trim() || busy}
                      onClick={() => {
                        const f = feedback;
                        setFeedback("");
                        setAskChanges(false);
                        resume({ feedback: f });
                      }}
                      className={`${ghost} mt-3 w-full`}
                    >
                      Revise plan
                    </button>
                  </div>
                )}
                <div className="flex gap-3">
                  <button type="button" onClick={() => setAskChanges((v) => !v)} disabled={pending.revisions_left === 0 || busy} className={ghost}>
                    Ask for changes
                  </button>
                  <button type="button" disabled={busy} onClick={() => resume({ approved: true, collect: effectiveCollect })} className={primary}>
                    Approve →
                  </button>
                </div>
              </div>
            </div>
          );
        })()}

        {/* 4. SOURCES */}
        {pending?.type === "review_sources" && (() => {
          const all = pending.candidates;
          const ticked = all.filter((c) => isTicked(c, pending.min_relevance));
          const cols = [
            { key: "pdf", title: "Papers and PDFs", items: all.filter((c) => c.kind === "paper") },
            { key: "web", title: "Web pages", items: all.filter((c) => c.kind !== "paper") },
          ];
          return (
            <>
              <div className="mb-6 flex flex-wrap items-end gap-5">
                <div>
                  <div className="kicker">The reading list</div>
                  <h2 className="mt-2 text-5xl leading-[1.05] tracking-tight">{all.length} sources found. Choose what to keep.</h2>
                </div>
                <div className="flex-1" />
                <div className="text-[15px]">
                  <b>{ticked.length}</b> chosen · {pending.max_sources > 0 ? `at most ${pending.max_sources}` : "no limit"} &nbsp;
                  <button type="button" className={link} onClick={() => setOverrides({ key: reviewKey, map: Object.fromEntries(all.map((c) => [c.id, true])) })}>
                    tick all
                  </button>{" "}
                  ·{" "}
                  <button type="button" className={link} onClick={() => setOverrides({ key: reviewKey, map: Object.fromEntries(all.map((c) => [c.id, false])) })}>
                    clear
                  </button>
                </div>
              </div>
              {pending.error ? (
                <p role="alert" className="mb-4 text-sm text-warning">
                  {pending.error}
                </p>
              ) : null}
              {pending.max_sources > 0 && ticked.length > pending.max_sources && (
                <p role="status" className="mb-4 border border-warning bg-warning-soft px-4 py-3 text-sm text-warning">
                  You ticked {ticked.length}, but at most {pending.max_sources} are collected: the best match of each question first, taking turns. Untick the weaker ones, or raise FETCH_MAX_SOURCES in .env.
                </p>
              )}
              <div className="grid gap-9 lg:grid-cols-2">
                {cols.map((col) => (
                  <div key={col.key}>
                    <div className="mb-1.5 border-b-2 border-foreground pb-2 font-serif text-[26px] font-semibold">
                      {col.title} <span className="text-base font-normal text-muted">&nbsp;{col.items.length}</span>
                    </div>
                    {col.items.length === 0 && <p className="py-3 text-sm text-muted">None found.</p>}
                    {col.items.map((c) => (
                      <div key={c.id} className={`${paper} mt-3 flex items-start gap-3.5 px-[18px] py-4`}>
                        <input
                          type="checkbox"
                          aria-label={`Keep ${c.title}`}
                          className="mt-1.5 h-4 w-4 accent-accent"
                          checked={isTicked(c, pending.min_relevance)}
                          onChange={(e) => setTick(c.id, e.target.checked)}
                          disabled={busy}
                        />
                        <div className="min-w-0 flex-1">
                          <a href={safeHref(c.url)} target="_blank" rel="noopener noreferrer nofollow" className="font-serif text-[19px] leading-snug hover:text-accent">
                            {c.title}
                          </a>
                          <div className="text-[13px] text-muted">
                            {c.site} · for: {c.question}{" "}
                            {c.snippet && (
                              <button type="button" className={`${link} text-[13px]`} onClick={() => setPreviewId(previewId === c.id ? null : c.id)}>
                                {previewId === c.id ? "Hide preview" : "Preview"}
                              </button>
                            )}
                          </div>
                          {previewId === c.id && c.snippet && <p className="mt-2 border-l-[3px] border-border pl-3 text-sm leading-relaxed">{c.snippet}</p>}
                        </div>
                        <span className={`rounded px-2 py-0.5 text-[11px] font-semibold ${c.score >= 3 ? "bg-success-soft text-success" : c.score === 2 ? "bg-warning-soft text-warning" : "bg-surface-hover text-muted"}`}>{c.score}/3</span>
                      </div>
                    ))}
                  </div>
                ))}
              </div>
              <div className="mt-7 flex justify-end gap-3">
                <button type="button" className={ghost} disabled={busy} onClick={() => resume({ selected: [] })}>
                  Skip collecting
                </button>
                <button type="button" className={primary} disabled={busy} onClick={() => resume({ selected: ticked.map((c) => c.id) })}>
                  Collect {ticked.length} sources →
                </button>
              </div>
            </>
          );
        })()}

        {/* 5. PROGRESS */}
        {cur === 4 && (() => {
          const stage = detail ? (detail.status === "done" ? 7 : (STAGE_OF[detail.step] ?? 0)) : stream.values.plan ? 4 : 1;
          const p = detail?.progress ?? {};
          const stateText = stream.values.plan ? (busy ? "Collecting sources, extracting evidence and writing" : "Stopped, or ended without a report") : busy ? "Preparing" : "";
          const collectedPdf = (detail?.collected ?? []).filter((c) => c.kind === "pdf" || c.kind === "paper").length;
          const collectedWeb = (detail?.collected ?? []).length - collectedPdf;
          return (
            <>
              <div className={`${paper} p-9`}>
                <div className="flex flex-wrap items-center gap-4">
                  <div className="kicker">In progress{detail ? ` · started ${ago(detail.startedAt)}` : ""}</div>
                  <div className="flex-1" />
                  <Link href="/graph" className={ghost}>
                    View pipeline
                  </Link>
                  <button type="button" onClick={() => setConfirmStop(true)} className={danger}>
                    Stop this run
                  </button>
                </div>
                <h2 className="my-3 text-5xl leading-[1.05] tracking-tight">
                  {STAGES[Math.min(stage, 6)] === "Evidence" ? "Reading and checking evidence" : STAGES[Math.min(stage, 6)] === "Writing" ? "Writing the report" : STAGES[Math.min(stage, 6)] === "Sources" ? "Collecting sources" : STAGES[Math.min(stage, 6)] === "Plan" ? "Planning" : "Getting ready"}{" "}
                  <span className="text-muted">(stage {Math.min(stage, 6) + 1} of 7)</span>
                </h2>
                {stateText && <p className="mb-4 text-sm text-muted">{stateText}</p>}
                {confirmStop && (
                  <div className="my-4 border border-danger p-4 text-sm leading-relaxed">
                    <b>Stop this run?</b> It stops within seconds, even in the middle of a model call. The facts found so far are kept, and you can start the goal again from Runs.
                    <div className="mt-3 flex gap-2">
                      <button type="button" onClick={stopRun} className={danger}>
                        Stop run
                      </button>
                      <button type="button" onClick={() => setConfirmStop(false)} className={ghost}>
                        Keep running
                      </button>
                    </div>
                  </div>
                )}
                <div className="flex gap-1.5">
                  {STAGES.map((s, i) => (
                    <div key={s} className="h-3 flex-1 rounded-[3px]" style={{ background: i < stage ? "var(--foreground)" : i === stage ? "var(--accent)" : "var(--border)" }} />
                  ))}
                </div>
                <div className="mt-1.5 flex gap-1.5 text-xs text-muted">
                  {STAGES.map((s, i) => (
                    <span key={s} className={`flex-1 ${i === stage ? "font-semibold text-accent" : ""}`}>
                      {s}
                    </span>
                  ))}
                </div>
                {detail?.progress.current && (
                  <p className="mt-4 text-sm text-muted">
                    <span className="font-semibold text-foreground">Now: </span>
                    {detail.progress.current}
                  </p>
                )}
              </div>
              <div className="mt-5 grid gap-5 md:grid-cols-3">
                <div className={`${paper} px-7 py-6`}>
                  <div className="font-serif text-6xl leading-none">
                    {p.questions_done ?? 0}
                    <span className="text-4xl text-muted"> of {p.questions_total ?? "?"}</span>
                  </div>
                  <div className="mt-1.5 text-sm text-muted">questions answered</div>
                </div>
                <div className={`${paper} px-7 py-6`}>
                  <div className="font-serif text-6xl leading-none">{p.evidence ?? 0}</div>
                  <div className="mt-1.5 text-sm text-muted">verified facts kept</div>
                </div>
                <div className={`${paper} px-7 py-6`}>
                  <div className="font-serif text-6xl leading-none">{(detail?.collected ?? []).length}</div>
                  <div className="mt-1.5 text-sm text-muted">sources collected: {collectedPdf} PDFs and papers, {collectedWeb} web pages</div>
                </div>
              </div>
              <div className={`${paper} mt-5 px-7 py-5`}>
                <div className="mb-2 text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">Newswire</div>
                {detail && detail.events.length > 0 ? (
                  <ul className="flex flex-col gap-1 text-[15px] leading-relaxed">
                    {[...detail.events].reverse().slice(0, 6).map((e, i) => (
                      <li key={`${e.t}-${i}`}>
                        <b>{new Date(e.t).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</b> &nbsp;{e.text}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-muted">Nothing recorded yet.</p>
                )}
                {threadId && (
                  <Link href={`/runs/${threadId}`} className={`${link} mt-3 inline-block`}>
                    Watch this run in detail →
                  </Link>
                )}
              </div>
            </>
          );
        })()}

        {/* 6. REPORT */}
        {slug && (
          <div className="mx-auto max-w-3xl py-10 text-center">
            <div className="kicker">The report</div>
            <h2 className="my-3 text-5xl leading-none tracking-tight sm:text-6xl">Your issue is on the press.</h2>
            <p className="font-serif text-2xl italic text-muted">
              {stream.values.stats
                ? `${stream.values.stats.words.toLocaleString()} words, ${stream.values.stats.evidence} verified facts across ${stream.values.stats.sections} chapters.`
                : "Open it to read."}
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-3">
              <Link href={`/research/${slug}`} className={primary}>
                Open the report →
              </Link>
              <button type="button" onClick={startOver} className={ghost}>
                New assignment
              </button>
              <Link href="/reports" className={ghost}>
                All reports
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default function DeepResearchPage() {
  return (
    <Suspense fallback={null}>
      <DeepResearchForm />
    </Suspense>
  );
}
