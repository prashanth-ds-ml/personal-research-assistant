"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useStream } from "@langchain/langgraph-sdk/react";
import { ResumeBanner } from "@/components/resume-banner";
import { useRunThread } from "@/lib/use-run-thread";
import { apiUrl } from "@/lib/api-url";
import { safeHref } from "@/lib/safe-href";
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

// Must be absolute - useStream does `new URL(apiUrl)` internally.

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
  const [collectChoice, setCollectChoice] = useState<"gaps" | "all" | "none" | null>(null);
  const [seeds, setSeeds] = useState("");

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
    setFeedback("");
    setSeeds("");
    setCollectChoice(null);
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
  const gaps = pending?.type === "approve_plan" ? (pending.coverage ?? []).filter((r) => r.status !== "answered") : [];
  const effectiveCollect: "gaps" | "all" | "none" = collectChoice ?? (gaps.length > 0 ? "gaps" : "none");
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
      { config: { configurable: { seed_urls: seeds } }, ...keepAlive }
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
            ? stream.isLoading
              ? "Collecting sources, extracting evidence and writing (this takes a while)"
              : "Stopped, or ended without a report. Open the run page (Watch this run in detail) to see what happened"
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
            Nothing has been downloaded yet. Tick what you want in your library; the best matches are ticked already.{" "}
            {pending.max_sources > 0 ? `At most ${pending.max_sources}` : "All of them"} will be collected, one at a time. Web pages are less
            reliable than papers.
          </p>
          {pending.error ? (
            <p role="alert" className="text-xs text-warning">
              {pending.error}
            </p>
          ) : null}
          {[
            { key: "pdf", label: "PDFs and papers", icon: <FileText className="h-4 w-4" />, items: pending.candidates.filter((c) => c.kind === "paper") },
            { key: "web", label: "Web pages", icon: <Globe className="h-4 w-4" />, items: pending.candidates.filter((c) => c.kind !== "paper") },
          ].map((section) => (
            <div key={section.key} className="flex flex-col gap-3 border-t border-border pt-3">
              <div className="flex items-center gap-1.5 text-sm font-medium">
                {section.icon}
                {section.label} ({section.items.length}, {section.items.filter((c) => isTicked(c, pending.min_relevance)).length} ticked)
              </div>
              {section.items.length === 0 ? <p className="text-xs text-muted">None found.</p> : null}
              {Array.from(new Set(section.items.map((c) => c.question_index))).map((qi) => {
                const group = section.items.filter((c) => c.question_index === qi);
                return (
                  <div key={qi} className="flex flex-col gap-2">
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
                            <a href={safeHref(c.url)} target="_blank" rel="noopener noreferrer nofollow" className="font-medium hover:text-accent hover:underline">
                              {c.title}
                            </a>
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
            </div>
          ))}
          {pending.max_sources > 0 && pending.candidates.filter((c) => isTicked(c, pending.min_relevance)).length > pending.max_sources ? (
            <p role="status" className="rounded-xl bg-warning-soft px-3 py-2 text-xs text-warning">
              You ticked {pending.candidates.filter((c) => isTicked(c, pending.min_relevance)).length}, but at most {pending.max_sources} are
              collected: the best match of each question first, taking turns across the questions. Untick the weaker ones, or raise
              FETCH_MAX_SOURCES in .env to collect more.
            </p>
          ) : null}
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
            <div className="text-xs font-medium text-muted">Questions I will answer, and what your library has on each</div>
            <ol className="mt-1 flex list-decimal flex-col gap-1.5 pl-5 text-sm">
              {pending.plan.sub_questions.map((q, i) => {
                const row = pending.coverage?.find((r) => r.index === i);
                return (
                  <li key={q}>
                    {q}
                    {row ? (
                      <span
                        className={`ml-2 rounded-full px-2 py-0.5 text-[11px] font-medium ${
                          row.status === "answered" ? "bg-success-soft text-success" : row.status === "thin" ? "bg-warning-soft text-warning" : "bg-surface-hover text-muted"
                        }`}
                        title={row.titles.join(" | ")}
                      >
                        {row.status === "answered" ? `covered (${row.relevant} documents)` : row.status === "thin" ? "thin (1 document)" : "nothing in the library"}
                      </span>
                    ) : null}
                  </li>
                );
              })}
            </ol>
            {gaps.length > 0 && (pending.coverage?.length ?? 0) > 0 ? (
              <p role="status" className="mt-2 rounded-xl bg-warning-soft px-3 py-2 text-xs text-warning">
                {gaps.length} of {pending.coverage?.length} questions are not well covered by your library
                {gaps.length * 2 >= (pending.coverage?.length ?? 0) ? ". With this little material the report would mostly say what is missing: collecting sources first is strongly advised" : ""}.
              </p>
            ) : null}
          </div>
          <fieldset className="flex flex-col gap-1.5 text-sm" disabled={stream.isLoading}>
            <legend className="text-xs font-medium text-muted">Collect new sources before researching?</legend>
            {(
              [
                { value: "gaps", label: `Yes, for the ${gaps.length} question(s) the library does not cover well`, off: gaps.length === 0 },
                { value: "all", label: "Yes, for every question", off: false },
                { value: "none", label: "No, use the library as it is", off: false },
              ] as const
            ).map((o) => (
              <label key={o.value} className={`flex items-center gap-2 ${o.off ? "opacity-50" : ""}`}>
                <input
                  type="radio"
                  name="collect"
                  className="h-4 w-4 accent-accent"
                  checked={effectiveCollect === o.value}
                  disabled={o.off}
                  onChange={() => setCollectChoice(o.value)}
                />
                {o.label}
              </label>
            ))}
            <span className="text-xs text-muted">
              You will see everything it finds, as PDFs/papers and web pages separately, and choose what to keep.
            </span>
          </fieldset>
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
            <button type="button" className={primary} disabled={stream.isLoading} onClick={() => resume({ approved: true, collect: effectiveCollect })}>
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
