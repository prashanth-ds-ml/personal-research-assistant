"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useStream } from "@langchain/langgraph-sdk/react";
import { ResumeBanner } from "@/components/resume-banner";
import { useRunThread } from "@/lib/use-run-thread";
import { Activity, AlertCircle, ArrowRight, CheckCircle2, FileText, Globe, MessageCircleQuestion, ListChecks } from "lucide-react";

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
type ApproveInterrupt = { type: "approve_plan"; plan: Plan; revisions_left: number };
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

// Must be absolute - useStream does `new URL(apiUrl)` internally.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001/api";

function reportSlug(reportPath?: string): string | null {
  const file = reportPath?.split(/[\\/]/).pop();
  return file ? file.replace(/\.md$/, "") : null;
}

const card = "flex flex-col gap-4 rounded-2xl border border-border bg-surface p-5 shadow-sm";
const input =
  "w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20";
const primary =
  "flex w-fit items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-accent-foreground shadow-sm shadow-accent/30 transition-transform hover:scale-[1.03] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50";
const secondary =
  "flex w-fit items-center gap-2 rounded-full border border-border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-surface-hover disabled:opacity-50";

function DeepResearchForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // "Start this goal again" (from a run that was lost or stopped) arrives with the goal in the address.
  const [goal, setGoal] = useState(() => searchParams.get("goal") ?? "");
  const [answers, setAnswers] = useState<string[]>([]);
  const [feedback, setFeedback] = useState("");
  const [fetchNew, setFetchNew] = useState(false);
  const [seeds, setSeeds] = useState("");

  // Remember the run's thread so leaving this page does not cancel it (see use-run-thread.ts).
  const { threadId, remember, forget } = useRunThread("deep-research-thread");
  const stream = useStream<DeepState>({
    apiUrl: API_URL,
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
    setFeedback("");
    setSeeds("");
    setFetchNew(false);
  };

  // The graph pauses (LangGraph `interrupt`) to ask questions / show the plan.
  // Only our own two interrupt shapes are acted on (LangGraph can also report a `{when: "breakpoint"}` pause).
  const raw = (stream.interrupt?.value ?? null) as { type?: string } | null;
  const pending =
    raw && (raw.type === "clarify" || raw.type === "approve_plan" || raw.type === "review_sources")
      ? (raw as DeepInterrupt)
      : null;

  // Which candidate sources are ticked. Defaults come from the relevance score; the user's clicks override them.
  // Kept per interrupt so a new list never inherits an old one's ticks (derived state, no effect needed).
  const reviewKey = pending?.type === "review_sources" ? pending.candidates.map((c) => c.id).join("|") : "";
  const [overrides, setOverrides] = useState<{ key: string; map: Record<string, boolean> }>({ key: "", map: {} });
  const ticks = overrides.key === reviewKey ? overrides.map : {};
  const isTicked = (c: ReviewCandidate, min: number) => ticks[c.id] ?? c.score >= min;
  const setTick = (id: string, value: boolean) => setOverrides({ key: reviewKey, map: { ...ticks, [id]: value } });
  const slug = reportSlug(stream.values.report_path);
  const started = stream.isLoading || Boolean(stream.values.goal) || Boolean(pending);

  // A remembered thread the server no longer has (backend restarted, in-memory threads are gone) would leave the
  // page stuck on an error: drop it so the goal form comes back.
  useEffect(() => {
    if (threadId && stream.error && !stream.isLoading && !stream.values.goal && /404|not found/i.test(String(stream.error))) {
      forget();
    }
  }, [threadId, stream.error, stream.isLoading, stream.values.goal, forget]);

  const resume = (value: unknown) => {
    if (stream.isLoading) return; // a double click must not resume the same pause twice
    stream.submit(undefined, { command: { resume: value }, ...keepAlive });
  };

  const start = (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim() || stream.isLoading) return;
    setAnswers([]);
    setFeedback("");
    stream.submit(
      { goal },
      { config: { configurable: { collect_sources: fetchNew, seed_urls: seeds } }, ...keepAlive }
    );
  };

  const sendAnswers = (questions: string[]) => {
    const text = questions
      .map((q, i) => (answers[i]?.trim() ? `${q}\n  -> ${answers[i].trim()}` : ""))
      .filter(Boolean)
      .join("\n");
    setAnswers([]);
    resume(text);
  };

  const stage = slug
    ? "Done"
    : pending?.type === "clarify"
      ? "Waiting for your answers"
      : pending?.type === "approve_plan"
        ? "Waiting for plan approval"
        : pending?.type === "review_sources"
          ? "Waiting for you to choose sources"
          : stream.values.plan
            ? "Collecting sources, extracting evidence and writing (this takes a while)"
            : stream.isLoading
              ? "Preparing"
              : "";

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Deep Research</h1>
        <p className="mt-1 text-sm text-muted">
          Give a goal. The assistant asks what it needs to know, shows you a research plan to approve, then builds a
          long cited report from your document library - entirely on local models.
        </p>
      </div>

      {active && <ResumeBanner loading={stream.isLoading} noun="goal" onReset={startOver} />}

      <form onSubmit={start} className={card}>
        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-medium text-muted">Goal</span>
          <textarea
            className={`${input} min-h-24 resize-y`}
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="e.g. Should our team adopt hybrid retrieval for the clinical guideline search? Cover accuracy, failure modes and cost."
            disabled={stream.isLoading || Boolean(pending) || active}
          />
        </label>
        <label className="flex items-start gap-2">
          <input
            id="fetch-new"
            type="checkbox"
            className="mt-1 h-4 w-4 accent-accent"
            checked={fetchNew}
            onChange={(e) => setFetchNew(e.target.checked)}
            disabled={stream.isLoading || Boolean(pending) || active}
          />
          <span className="text-sm">
            Find and collect new sources first
            <span className="block text-xs text-muted">
              After you approve the plan, searches the web, arXiv and Europe PMC for each question and shows you what it
              found. You choose which pages and papers to save into your library (adds a few minutes).
            </span>
          </span>
        </label>
        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-medium text-muted">Pages or PDFs to add first (optional, one per line)</span>
          <textarea
            id="seed-urls"
            className={`${input} min-h-16 resize-y`}
            value={seeds}
            onChange={(e) => setSeeds(e.target.value)}
            placeholder="https://example.org/a-useful-article"
            disabled={stream.isLoading || Boolean(pending) || active}
          />
        </label>
        <button type="submit" disabled={stream.isLoading || Boolean(pending) || active || !goal.trim()} className={primary}>
          {stream.isLoading ? "Working..." : "Start"}
          {!stream.isLoading && <ArrowRight className="h-4 w-4" />}
        </button>
      </form>

      {stream.error ? (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-warning/30 bg-warning-soft px-4 py-3 text-sm text-warning">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {String(stream.error)}
        </div>
      ) : null}

      {threadId && (
        <Link href={`/runs/${threadId}`} className="flex w-fit items-center gap-1.5 text-xs font-medium text-accent hover:underline">
          <Activity className="h-3.5 w-3.5" />
          Watch this run in detail
        </Link>
      )}

      {started && stage && (
        <div role="status" aria-live="polite" className="flex items-center gap-3 text-sm text-muted">
          <span>
            <span className="font-medium text-foreground">Status: </span>
            {stage}
          </span>
          {stream.isLoading && (
            <button type="button" className="text-xs underline hover:text-foreground" onClick={() => stream.stop()}>
              Stop
            </button>
          )}
        </div>
      )}

      {stream.values.library_update?.documents !== undefined && (
        <div className="text-xs text-muted">
          Library: {stream.values.library_update.documents} documents
          {stream.values.library_update.added ? `, ${stream.values.library_update.added} new indexed for this run` : ""}
          {stream.values.library_update.failed?.length ? `, ${stream.values.library_update.failed.length} could not be read` : ""}
        </div>
      )}
      {stream.values.collect_report && !stream.values.collect_report.error && (
        <div className="text-xs text-muted">
          Collected sources: {stream.values.collect_report.saved ?? 0} added to your library
          {stream.values.collect_report.pages !== undefined ? ` (${stream.values.collect_report.pages} web pages, ${stream.values.collect_report.papers ?? 0} papers)` : ""},{" "}
          {stream.values.collect_report.skipped ?? 0} skipped
          {stream.values.collect_report.failed ? `, ${stream.values.collect_report.failed} failed` : ""}
          {stream.values.collect_report.folder ? ` (details in ${stream.values.collect_report.folder}/manifest.json)` : ""}
        </div>
      )}
      {stream.values.collect_report?.error && (
        <div className="text-xs text-warning">
          Could not fetch new sources ({stream.values.collect_report.error}); researching your existing library.
        </div>
      )}
      {stream.values.library_update?.error && (
        <div className="text-xs text-warning">
          Could not update the library ({stream.values.library_update.error}); using the existing index.
        </div>
      )}

      {pending?.type === "clarify" && (
        <div className={card}>
          <div className="flex items-center gap-2 font-medium">
            <MessageCircleQuestion className="h-4 w-4 text-accent" />A few questions before I start
          </div>
          <p className="text-xs text-muted">Answer what you can; leave any blank to let me decide.</p>
          {pending.questions.map((q, i) => (
            <label key={q} className="flex flex-col gap-1.5">
              <span className="text-sm">{q}</span>
              <input
                className={input}
                value={answers[i] ?? ""}
                onChange={(e) => setAnswers((a) => Object.assign([...a], { [i]: e.target.value }))}
              />
            </label>
          ))}
          <button type="button" className={primary} disabled={stream.isLoading} onClick={() => sendAnswers(pending.questions)}>
            Continue <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      )}

      {pending?.type === "review_sources" && (
        <div className={card}>
          <div className="flex items-center gap-2 font-medium">
            <Globe className="h-4 w-4 text-accent" />
            Sources found for your questions
          </div>
          <p className="text-xs text-muted">
            Nothing has been downloaded yet. Tick what you want in your library; the best matches are ticked already. At
            most {pending.max_sources} will be collected, one at a time. Web pages are less reliable than papers.
          </p>
          {pending.error ? (
            <p role="alert" className="text-xs text-warning">
              {pending.error}
            </p>
          ) : null}
          {Array.from(new Set(pending.candidates.map((c) => c.question_index))).map((qi) => {
            const group = pending.candidates.filter((c) => c.question_index === qi);
            return (
              <div key={qi} className="flex flex-col gap-2 border-t border-border pt-3">
                <div className="text-xs font-medium text-muted">{group[0].question}</div>
                {group.map((c) => (
                  <label key={c.id} className="flex items-start gap-2 text-sm">
                    <input
                      type="checkbox"
                      className="mt-1 h-4 w-4 accent-accent"
                      checked={isTicked(c, pending.min_relevance)}
                      onChange={(e) => setTick(c.id, e.target.checked)}
                      disabled={stream.isLoading}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex flex-wrap items-center gap-2">
                        <a href={c.url} target="_blank" rel="noopener noreferrer nofollow" className="font-medium hover:text-accent hover:underline">
                          {c.title}
                        </a>
                        <span className="flex items-center gap-1 rounded-full bg-surface-hover px-2 py-0.5 text-[11px] text-muted">
                          {c.kind === "paper" ? <FileText className="h-3 w-3" /> : <Globe className="h-3 w-3" />}
                          {c.kind === "paper" ? "paper" : "web page"}
                        </span>
                        <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${c.score >= 3 ? "bg-success-soft text-success" : "bg-warning-soft text-warning"}`}>
                          relevance {c.score}/3
                        </span>
                      </span>
                      <span className="block truncate text-xs text-muted">{c.site}</span>
                      {c.snippet ? <span className="mt-0.5 block text-xs text-muted">{c.snippet}</span> : null}
                    </span>
                  </label>
                ))}
              </div>
            );
          })}
          <div className="flex flex-wrap items-center gap-3 border-t border-border pt-4">
            <button
              type="button"
              className={primary}
              disabled={stream.isLoading}
              onClick={() =>
                resume({ selected: pending.candidates.filter((c) => isTicked(c, pending.min_relevance)).map((c) => c.id) })
              }
            >
              Collect {pending.candidates.filter((c) => isTicked(c, pending.min_relevance)).length} selected <ArrowRight className="h-4 w-4" />
            </button>
            <button type="button" className={secondary} disabled={stream.isLoading} onClick={() => resume({ selected: [] })}>
              Skip collecting
            </button>
          </div>
        </div>
      )}

      {pending?.type === "approve_plan" && (
        <div className={card}>
          <div className="flex items-center gap-2 font-medium">
            <ListChecks className="h-4 w-4 text-accent" />
            Research plan: {pending.plan.title}
          </div>
          <div>
            <div className="text-xs font-medium text-muted">Questions I will answer from your library</div>
            <ol className="mt-1 list-decimal pl-5 text-sm">
              {pending.plan.sub_questions.map((q) => (
                <li key={q}>{q}</li>
              ))}
            </ol>
          </div>
          <div>
            <div className="text-xs font-medium text-muted">Report outline</div>
            <ul className="mt-1 list-disc pl-5 text-sm">
              {pending.plan.outline.map((s) => (
                <li key={s.title}>
                  <span className="font-medium">{s.title}</span>
                  {s.brief ? <span className="text-muted"> - {s.brief}</span> : null}
                  {s.synthesis ? <span className="text-muted"> (synthesised from the other sections)</span> : null}
                </li>
              ))}
            </ul>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <button type="button" className={primary} disabled={stream.isLoading} onClick={() => resume({ approved: true })}>
              Approve and run <ArrowRight className="h-4 w-4" />
            </button>
          </div>
          {pending.revisions_left > 0 && (
            <div className="flex flex-col gap-2 border-t border-border pt-4">
              <span className="text-xs font-medium text-muted">
                Or ask for changes ({pending.revisions_left} revision{pending.revisions_left === 1 ? "" : "s"} left)
              </span>
              <input
                className={input}
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                placeholder="e.g. add a section on cost, drop the history of RAG"
              />
              <button
                type="button"
                className={secondary}
                disabled={!feedback.trim() || stream.isLoading}
                onClick={() => {
                  const f = feedback;
                  setFeedback("");
                  resume({ feedback: f });
                }}
              >
                Revise plan
              </button>
            </div>
          )}
        </div>
      )}

      {slug && (
        <div role="status" className="flex items-center gap-3 rounded-2xl border border-success/30 bg-success-soft px-5 py-4 text-sm text-success">
          <CheckCircle2 className="h-5 w-5 shrink-0" />
          <span className="flex-1">
            Report ready
            {stream.values.stats
              ? ` - ${stream.values.stats.words.toLocaleString()} words, ${stream.values.stats.evidence} verified facts`
              : ""}
            .
          </span>
          <Link href={`/research/${slug}`} className="font-medium underline">
            Open report
          </Link>
        </div>
      )}
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
