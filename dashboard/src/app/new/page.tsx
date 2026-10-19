"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useStream } from "@langchain/langgraph-sdk/react";
import { ResumeBanner } from "@/components/resume-banner";
import { useRunThread } from "@/lib/use-run-thread";
import { apiUrl } from "@/lib/api-url";
import Link from "next/link";
import { ErrorCard } from "@/components/error-card";
type Stage = "profile" | "query" | "research" | "reflect" | "done";

interface ResearchState {
  research_topic?: string;
  search_query?: string;
  research_loop_count?: number;
  running_summary?: string;
  report_path?: string;
  entity_topics?: string[];
}

const ASSISTANT_ID =
  process.env.NEXT_PUBLIC_LANGGRAPH_ASSISTANT_ID ?? "research_assistant";

function reportSlug(reportPath?: string): string | null {
  if (!reportPath) return null;
  const file = reportPath.split(/[\\/]/).pop();
  return file ? file.replace(/\.md$/, "") : null;
}

function currentStage(values: ResearchState, done: boolean): Stage {
  if (done) return "done";
  if (values.entity_topics && values.entity_topics.length > 1) return "research";
  if (values.running_summary) return "reflect";
  if (values.research_loop_count) return "research";
  if (values.search_query) return "query";
  return "profile";
}

function NewResearchForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [topic, setTopic] = useState(() => searchParams.get("topic") ?? "");
  const [loops, setLoops] = useState(3);
  const [source, setSource] = useState<"web" | "local_docs">("web");

  // Remember the run's thread so leaving this page does not cancel it (see use-run-thread.ts).
  const { threadId, remember, forget } = useRunThread("quick-research-thread");
  const stream = useStream<ResearchState>({
    apiUrl: apiUrl(),
    assistantId: ASSISTANT_ID,
    threadId,
    onThreadId: remember,
    reconnectOnMount: () => window.localStorage, // same storage the thread id lives in
  });
  const active = Boolean(threadId);

  // Arriving with ?topic=... ("Continue researching this topic") means a new run: drop any remembered one.
  const prefilled = Boolean(searchParams.get("topic"));
  useEffect(() => {
    if (prefilled) {
      forget();
      router.replace("/new"); // the topic is already in the field; a reload must not forget the run again
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only on arrival
  }, []);

  // A remembered thread the server no longer has (backend restarted) would leave the page stuck on an error.
  useEffect(() => {
    if (threadId && stream.error && !stream.isLoading && !stream.values.research_topic && /404|not found/i.test(String(stream.error))) {
      forget();
    }
  }, [threadId, stream.error, stream.isLoading, stream.values.research_topic, forget]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim() || stream.isLoading) return;
    stream.submit(
      { research_topic: topic },
      {
        config: {
          configurable: {
            max_web_research_loops: Math.min(10, Math.max(0, Math.round(loops) || 0)),
            // "web" leaves search_api to the backend default (SEARCH_API env / duckduckgo).
            ...(source === "local_docs" ? { search_api: "local_docs" } : {}),
          },
        },
        onDisconnect: "continue",
        streamResumable: true,
      }
    );
  };

  const slug = reportSlug(stream.values.report_path);
  const done = Boolean(slug);
  const started = stream.isLoading || Boolean(stream.values.research_topic);
  const comparing = (stream.values.entity_topics?.length ?? 0) > 1;

  const locked = stream.isLoading || active;
  const stages: { key: Stage; label: string }[] = [
    { key: "profile", label: "Loading profile & prior notes" },
    { key: "query", label: "Generating search query" },
    { key: "research", label: "Researching the web" },
    { key: "reflect", label: "Reflecting on knowledge gaps" },
    { key: "done", label: "Report written" },
  ];
  const stageIdx = stages.findIndex((x) => x.key === currentStage(stream.values, done));
  const lab = "text-[11px] font-semibold uppercase tracking-widest text-muted";
  const step = "h-9 w-9 rounded-full border border-border text-lg hover:border-accent disabled:opacity-40";

  return (
    <div className="mx-auto max-w-4xl">
      <div className="kicker">The short column</div>
      <h1 className="mt-1 text-5xl leading-none">Quick research</h1>
      <p className="mb-6 mt-3 text-sm text-muted">
        A short cited note in a few minutes. Calibrated by your profile and earlier notes, then saved to your vault. Comparisons (&quot;X vs Y&quot;) are detected and researched in parallel.
      </p>

      {active && (
        <div className="mb-5">
          <ResumeBanner
            loading={stream.isLoading}
            noun="research"
            onReset={() => {
              forget();
              setTopic("");
            }}
          />
        </div>
      )}

      <form onSubmit={handleSubmit} className="border border-border border-t-[3px] border-t-foreground bg-surface p-7">
        <label htmlFor="qt" className={lab}>
          Topic
        </label>
        <input
          id="qt"
          className="mt-2 w-full rounded border border-border bg-background px-3.5 py-3 text-[17px] outline-none focus:border-accent"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="What is the Model Context Protocol?"
          disabled={locked}
        />
        <div className="mt-5 flex flex-wrap items-end gap-8">
          <div>
            <div className={lab}>Max research loops</div>
            <div className="mt-2 flex items-center gap-3">
              <button type="button" aria-label="Fewer loops" className={step} disabled={locked} onClick={() => setLoops((n) => Math.max(0, n - 1))}>
                −
              </button>
              <b className="min-w-6 text-center text-[22px]">{loops}</b>
              <button type="button" aria-label="More loops" className={step} disabled={locked} onClick={() => setLoops((n) => Math.min(10, n + 1))}>
                +
              </button>
            </div>
          </div>
          <div>
            <label htmlFor="qs" className={lab}>
              Search
            </label>
            <select
              id="qs"
              className="mt-2 block rounded border border-border bg-background px-3 py-2.5 text-sm outline-none focus:border-accent"
              value={source}
              onChange={(e) => setSource(e.target.value as "web" | "local_docs")}
              disabled={locked}
            >
              <option value="web">Web</option>
              <option value="local_docs">Internal documents</option>
            </select>
          </div>
          <div className="flex-1" />
          {stream.isLoading ? (
            <button type="button" onClick={() => stream.stop()} className="rounded border border-danger px-5 py-2.5 text-sm font-semibold text-danger hover:bg-danger hover:text-accent-foreground">
              Stop
            </button>
          ) : (
            <button type="submit" disabled={locked || !topic.trim()} className="rounded bg-accent px-5 py-2.5 text-sm font-semibold text-accent-foreground hover:opacity-90 disabled:opacity-40">
              Start research →
            </button>
          )}
        </div>
      </form>

      {stream.error ? (
        <div className="mt-5">
          <ErrorCard error={stream.error} />
        </div>
      ) : null}

      {started && (
        <div className="mt-5 border border-border border-t-[3px] border-t-foreground bg-surface p-7">
          <ol className="flex flex-wrap gap-2" aria-label="Progress">
            {stages.map((x, i) => (
              <li
                key={x.key}
                aria-current={i === stageIdx ? "step" : undefined}
                className={`rounded border px-3 py-1.5 text-[13px] ${i < stageIdx ? "border-success text-success" : i === stageIdx ? "border-accent font-semibold text-accent" : "border-border text-muted"}`}
              >
                {x.label}
              </li>
            ))}
          </ol>
          {comparing && (
            <p className="mt-4 text-sm leading-relaxed text-muted">
              Researching {stream.values.entity_topics!.length} topics in parallel: {stream.values.entity_topics!.join(" · ")}
            </p>
          )}
          {!comparing && (
            <p className="mt-4 text-sm leading-[1.7] text-muted">
              {stream.values.search_query && (
                <>
                  Current query: <i>{stream.values.search_query}</i>
                  <br />
                </>
              )}
              {typeof stream.values.research_loop_count === "number" && `${stream.values.research_loop_count} research loop${stream.values.research_loop_count === 1 ? "" : "s"} completed so far`}
            </p>
          )}
          {!done && !comparing && stream.values.running_summary && (
            <details className="mt-3 rounded border border-border bg-background p-3">
              <summary className="cursor-pointer text-sm text-muted">Latest summary (in progress)</summary>
              <p className="mt-2 whitespace-pre-wrap text-sm text-muted">{stream.values.running_summary}</p>
            </details>
          )}
        </div>
      )}

      {done && slug && (
        <div role="status" className="mt-5 border border-success bg-success-soft p-6 text-success">
          <div className="flex items-center gap-3">
            <b className="flex-1 text-base">Research complete. Saved to your vault.</b>
            <Link href={`/research/${slug}`} className="rounded bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground">
              View report
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}

export default function NewResearchPage() {
  return (
    <Suspense fallback={null}>
      <NewResearchForm />
    </Suspense>
  );
}
