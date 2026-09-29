"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { useStream } from "@langchain/langgraph-sdk/react";
import { CheckCircle2, Search as SearchIcon, ArrowRight, AlertCircle } from "lucide-react";
import { PipelineStepper, type Stage } from "@/components/pipeline-stepper";

interface ResearchState {
  research_topic?: string;
  search_query?: string;
  research_loop_count?: number;
  running_summary?: string;
  report_path?: string;
  advocate_view?: string;
  critic_view?: string;
  entity_topics?: string[];
}

const ASSISTANT_ID =
  process.env.NEXT_PUBLIC_LANGGRAPH_ASSISTANT_ID ?? "research_assistant";
// Must be absolute - useStream does `new URL(apiUrl)` internally.
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:3001/api";

function reportSlug(reportPath?: string): string | null {
  if (!reportPath) return null;
  const file = reportPath.split(/[\\/]/).pop();
  return file ? file.replace(/\.md$/, "") : null;
}

function currentStage(values: ResearchState, done: boolean): Stage {
  if (done) return "done";
  if (values.advocate_view || values.critic_view) return "debate";
  if (values.entity_topics && values.entity_topics.length > 1) return "research";
  if (values.running_summary) return "reflect";
  if (values.research_loop_count) return "research";
  if (values.search_query) return "query";
  return "profile";
}

function NewResearchForm() {
  const searchParams = useSearchParams();
  const [topic, setTopic] = useState(() => searchParams.get("topic") ?? "");
  const [loops, setLoops] = useState(3);
  const [debateMode, setDebateMode] = useState(false);

  const stream = useStream<ResearchState>({
    apiUrl: API_URL,
    assistantId: ASSISTANT_ID,
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!topic.trim()) return;
    stream.submit(
      { research_topic: topic },
      {
        config: {
          configurable: { max_web_research_loops: loops, enable_debate_mode: debateMode },
        },
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
              disabled={stream.isLoading}
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
              disabled={stream.isLoading}
            />
          </label>

          <label className="flex items-center gap-2 pt-4">
            <input
              type="checkbox"
              className="h-4 w-4 accent-accent"
              checked={debateMode}
              onChange={(e) => setDebateMode(e.target.checked)}
              disabled={stream.isLoading}
            />
            <span className="text-sm">
              Debate mode
              <span className="ml-1.5 text-xs text-muted">(GPU advocate + CPU critic)</span>
            </span>
          </label>
        </div>

        <button
          type="submit"
          disabled={stream.isLoading || !topic.trim()}
          className="flex w-fit items-center gap-2 rounded-full bg-accent px-5 py-2.5 text-sm font-medium text-accent-foreground shadow-sm shadow-accent/30 transition-transform hover:scale-[1.03] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:scale-100"
        >
          {stream.isLoading ? "Researching..." : "Start Research"}
          {!stream.isLoading && <ArrowRight className="h-4 w-4" />}
        </button>
      </form>

      {stream.error ? (
        <div className="flex items-center gap-2 rounded-xl border border-warning/30 bg-warning-soft px-4 py-3 text-sm text-warning">
          <AlertCircle className="h-4 w-4 shrink-0" />
          {String(stream.error)}
        </div>
      ) : null}

      {started && (
        <div className="flex flex-col gap-5 rounded-2xl border border-border bg-surface p-5 shadow-sm">
          <PipelineStepper current={currentStage(stream.values, done)} debateEnabled={debateMode} />

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

          {!done && (stream.values.advocate_view || stream.values.critic_view) && (
            <div className="flex flex-col gap-2 rounded-xl bg-background p-3 text-sm">
              {stream.values.advocate_view && (
                <p><span className="font-medium text-success">In favor: </span>{stream.values.advocate_view}</p>
              )}
              {stream.values.critic_view && (
                <p><span className="font-medium text-warning">Concerns: </span>{stream.values.critic_view}</p>
              )}
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
        <div className="flex items-center gap-3 rounded-2xl border border-success/30 bg-success-soft px-5 py-4 text-sm text-success">
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
