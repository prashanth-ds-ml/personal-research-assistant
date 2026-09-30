const LANGSMITH_API = "https://api.smith.langchain.com";
const API_KEY = process.env.LANGSMITH_API_KEY;
const PROJECT_NAME = process.env.LANGSMITH_PROJECT ?? "personal-research-assistant";

interface LangSmithRun {
  id: string;
  trace_id: string;
  status: string;
  start_time: string;
  end_time: string | null;
  total_tokens: number | null;
  inputs?: { research_topic?: string };
  parent_run_ids?: string[];
  app_path?: string;
  extra?: { metadata?: { langgraph_node?: string } };
}

export interface TraceStep {
  node: string;
  durationMs: number | null;
  status: string;
}

export interface TraceSummary {
  status: string;
  totalTokens: number | null;
  startTime: string;
  endTime: string | null;
  appUrl: string;
  steps: TraceStep[];
}

let cachedSessionId: string | null = null;

async function getSessionId(): Promise<string | null> {
  if (!API_KEY) return null;
  if (cachedSessionId) return cachedSessionId;

  const res = await fetch(
    `${LANGSMITH_API}/sessions?name=${encodeURIComponent(PROJECT_NAME)}`,
    { headers: { "x-api-key": API_KEY }, cache: "no-store", signal: AbortSignal.timeout(3000) }
  );
  if (!res.ok) return null;
  const sessions: { id: string }[] = await res.json();
  cachedSessionId = sessions[0]?.id ?? null;
  return cachedSessionId;
}

/** Finds the LangSmith trace for a completed research run by matching the
 * exact topic string, and builds a per-node timeline from its child runs.
 * Returns null (never throws) if LangSmith isn't configured or no match is
 * found - trace embedding is a nice-to-have, not load-bearing. */
export async function findTraceForTopic(topic: string): Promise<TraceSummary | null> {
  try {
    const sessionId = await getSessionId();
    if (!sessionId || !API_KEY) return null;

    const rootRes = await fetch(`${LANGSMITH_API}/runs/query`, {
      method: "POST",
      headers: { "x-api-key": API_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ session: [sessionId], is_root: true, limit: 50 }),
      cache: "no-store",
      signal: AbortSignal.timeout(3000), // a slow or offline LangSmith must not hold up opening a report
    });
    if (!rootRes.ok) return null;
    const { runs: rootRuns }: { runs: LangSmithRun[] } = await rootRes.json();

    const match = rootRuns
      .filter((r) => r.inputs?.research_topic === topic)
      .sort((a, b) => (a.start_time < b.start_time ? 1 : -1))[0];
    if (!match) return null;

    const traceRes = await fetch(`${LANGSMITH_API}/runs/query`, {
      method: "POST",
      headers: { "x-api-key": API_KEY, "Content-Type": "application/json" },
      body: JSON.stringify({ trace: match.trace_id, limit: 100 }),
      cache: "no-store",
      signal: AbortSignal.timeout(3000), // a slow or offline LangSmith must not hold up opening a report
    });
    const traceRuns: LangSmithRun[] = traceRes.ok ? (await traceRes.json()).runs : [];

    const steps: TraceStep[] = traceRuns
      .filter((r) => (r.parent_run_ids?.length ?? 0) === 1 && r.extra?.metadata?.langgraph_node)
      .sort((a, b) => (a.start_time < b.start_time ? -1 : 1))
      .map((r) => ({
        node: r.extra!.metadata!.langgraph_node!,
        durationMs: r.end_time
          ? new Date(r.end_time).getTime() - new Date(r.start_time).getTime()
          : null,
        status: r.status,
      }));

    return {
      status: match.status,
      totalTokens: match.total_tokens,
      startTime: match.start_time,
      endTime: match.end_time,
      appUrl: `https://smith.langchain.com${match.app_path}`,
      steps,
    };
  } catch {
    return null;
  }
}
