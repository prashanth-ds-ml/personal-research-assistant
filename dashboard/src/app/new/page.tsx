"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useStream } from "@langchain/langgraph-sdk/react";
import { ResumeBanner } from "@/components/resume-banner";
import { useRunThread } from "@/lib/use-run-thread";
import { apiUrl } from "@/lib/api-url";
import { CheckCircle2, Search as SearchIcon, ArrowRight, AlertCircle } from "lucide-react";
import { PipelineStepper, type Stage } from "@/components/pipeline-stepper";

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

  return (
    <div className="flex flex-col gap-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">New Research</h1>
        <p className="mt-1 text-sm text-muted">
          Calibrated by your profile and prior notes, then archived back into your vault.
          Comparisons (&quot;X vs Y&quot;) are detected automatically and researched in parallel.
        </p>
      </div>

      {active && (
        <ResumeBanner
          loading={stream.isLoading}
          noun="research"
          onReset={() => {
            forget();
            setTopic("");
          }}
        />
      )}

      <form
        onSubmit={handleSubmit}
        className="flex flex-col gap-4 rounded-2xl border border-border bg-surface p-5 shadow-sm"
      >
        <label className="flex flex-col gap-1.5">
          <span className="text-xs font-medium text-muted">Topic</span>
          <div className="flex items-center gap-2 rounded-xl border border-border bg-background px-3 focus-within:border-accent focus-within:ring-2 focus-within:ring-accent/20">
            <SearchIcon className="h-4 w-4 shrink-0 text-muted" />
            <input
              className="w-full bg-transparent py-2.5 text-sm outline-none placeholder:text-muted"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="What is the Model Context Protocol?"
              disabled={stream.isLoading || active}
            />
          </div>
        </label>

        <div className="flex items-center gap-6">
          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-muted">Max research loops</span>
            <input
              type="number"
              min={0}
              max={10}
              className="w-24 rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
              value={loops}
              onChange={(e) => setLoops(Number(e.target.value))}
              disabled={stream.isLoading || active}
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-xs font-medium text-muted">Search</span>
            <select
              className="rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
              value={source}
              onChange={(e) => setSource(e.target.value as "web" | "local_docs")}
              disabled={stream.isLoading || active}
            >
              <option value="web">Web</option>
              <option value="local_docs">Internal documents</option>
            </select>
          </label>

        </div>

        <button
          type="submit"
          disabled={stream.isLoading || active || !topic.trim()}
          className="flex w-fit items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-accent-foreground shadow-sm shadow-accent/30 transition-transform hover:scale-[1.03] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
        >
          {stream.isLoading ? "Researching..." : "Start Research"}
          {!stream.isLoading && <ArrowRight className="h-4 w-4" />}
        </button>
      </form>

      {stream.error ? (
        <div role="alert" className="flex items-center gap-2 rounded-xl border border-warning/30 bg-warning-soft px-4 py-3 text-sm text-warning">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {String(stream.error)}
        </div>
      ) : null}

      {stream.isLoading && (
        <div role="status" aria-live="polite" className="flex items-center gap-3 text-sm text-muted">
          Researching...
          <button type="button" className="text-xs underline hover:text-foreground" onClick={() => stream.stop()}>
            Stop
          </button>
        </div>
      )}

      {started && (
        <div className="flex flex-col gap-5 rounded-2xl border border-border bg-surface p-5 shadow-sm">
          <PipelineStepper current={currentStage(stream.values, done)} />

          {comparing && (
            <div className="rounded-xl bg-background px-3 py-2 text-sm">
              <span className="text-muted">Researching {stream.values.entity_topics!.length} topics in parallel: </span>
              {stream.values.entity_topics!.join(" · ")}
            </div>
          )}

          {!comparing && stream.values.search_query && (
            <div className="rounded-xl bg-background px-3 py-2 text-sm">
              <span className="text-muted">Current query: </span>
              {stream.values.search_query}
            </div>
          )}

          {!comparing && typeof stream.values.research_loop_count === "number" && (
            <div className="text-xs text-muted">
              {stream.values.research_loop_count} research loop
              {stream.values.research_loop_count === 1 ? "" : "s"} completed so far
            </div>
          )}

          {!done && !comparing && stream.values.running_summary && (
            <details className="rounded-xl bg-background p-3">
              <summary className="cursor-pointer text-sm text-muted">
                Latest summary (in progress)
              </summary>
              <p className="mt-2 whitespace-pre-wrap text-sm text-muted">
                {stream.values.running_summary}
              </p>
            </details>
          )}
        </div>
      )}

      {done && slug && (
        <div role="status" className="flex items-center gap-3 rounded-2xl border border-success/30 bg-success-soft px-5 py-4 text-sm text-success">
          <CheckCircle2 className="h-5 w-5 shrink-0" />
          <span className="flex-1">Research complete.</span>
          <a
            href={`/research/${slug}`}
            className="rounded-full bg-success px-3 py-1.5 text-xs font-medium text-white"
          >
            View report
          </a>
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
