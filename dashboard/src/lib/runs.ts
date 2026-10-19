import fs from "node:fs/promises";
import path from "node:path";

// Reads the run records the Python graph writes to <vault>/.runs/<run id>.json (see src/research_assistant/runlog.py).
// They live in the vault, not in LangGraph's in-memory store, so a run still shows up after the backend restarts.

const VAULT_PATH = process.env.VAULT_PATH ?? "";
const UPSTREAM = (process.env.LANGGRAPH_API_URL || "http://127.0.0.1:2025").replace(/\/$/, "");
const ID_RE = /^[\w.-]{1,80}$/;
/** A running record that has not changed for this long is flagged as possibly stuck. */
export const STALL_MS = 15 * 60 * 1000;

export type RunStatus = "running" | "waiting" | "done" | "failed" | "stopped" | "stalled" | "lost";

export interface RunEvent {
  t: string;
  text: string;
  level?: string;
}

export interface RunProgress {
  questions_total?: number;
  questions_done?: number;
  evidence?: number;
  sections_total?: number;
  sections_done?: number;
  current?: string;
}

export interface RunSummary {
  id: string;
  goal: string;
  status: RunStatus;
  /** What the record itself says (before checking whether the backend still knows the run). */
  recordedStatus: string;
  step: string;
  waitingFor: string | null;
  startedAt: string;
  updatedAt: string;
  progress: RunProgress;
  reportPath: string;
  error: string;
  note: string;
}

/** A source the collector saved, skipped or failed on during this run. */
export interface CollectedRow {
  title: string;
  url: string;
  kind: string;
  status: string;
  reason: string;
}

/** A document the report's evidence came from. */
export interface UsedSource {
  title: string;
  url: string;
  kind: string;
  group: string;
  facts: number;
  cited: number;
}

/** A clarifying question and what the user answered ("" = left to the assistant). */
export interface QA {
  question: string;
  answer: string;
}

export interface CoverageRec {
  index: number;
  question: string;
  status: string;
  relevant: number;
  titles: string[];
}

/** The research plan the run is following. */
export interface PlanInfo {
  title: string;
  questions: string[];
  outline: string[];
}

export interface RunDetail extends RunSummary {
  /** The clarifying questions asked at the start (shown even while the run still waits for the answers). */
  clarifyQuestions: string[];
  clarifications: QA[];
  plan: PlanInfo | null;
  coverage: CoverageRec[];
  /** Verified facts found for each plan question so far, by question number. */
  questionFacts: number[];
  collected: CollectedRow[];
  sources: UsedSource[];
  events: RunEvent[];
  stats: Record<string, number>;
  backendReachable: boolean;
}

export function validRunId(id: string): boolean {
  return ID_RE.test(id) && !id.includes("..");
}

function runsDir(): string | null {
  return VAULT_PATH ? path.join(VAULT_PATH, ".runs") : null;
}

async function readRecord(id: string): Promise<Record<string, unknown> | null> {
  const dir = runsDir();
  if (!dir || !validRunId(id)) return null;
  try {
    const data = JSON.parse(await fs.readFile(path.join(dir, `${id}.json`), "utf-8"));
    return data && typeof data === "object" ? (data as Record<string, unknown>) : null;
  } catch {
    return null;
  }
}

const str = (v: unknown): string => (typeof v === "string" ? v : "");

type ThreadState = "busy" | "idle" | "interrupted" | "error" | "missing" | "unreachable";

/** What the research engine keeps for a run: the questions it asked, the answers, the plan and the coverage check.
 * Used when the run record (written by older code) does not have them. Never throws. */
async function threadValues(id: string): Promise<Record<string, unknown> | null> {
  try {
    const res = await fetch(`${UPSTREAM}/threads/${encodeURIComponent(id)}/state`, { cache: "no-store", signal: AbortSignal.timeout(2000) });
    if (!res.ok) return null;
    const body = (await res.json()) as { values?: Record<string, unknown> };
    return body.values && typeof body.values === "object" ? body.values : null;
  } catch {
    return null;
  }
}

async function threadState(id: string): Promise<ThreadState> {
  try {
    const res = await fetch(`${UPSTREAM}/threads/${encodeURIComponent(id)}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(2000),
    });
    if (res.status === 404) return "missing";
    if (!res.ok) return "unreachable";
    const body = (await res.json()) as { status?: string };
    return (body.status as ThreadState) ?? "idle";
  } catch {
    return "unreachable";
  }
}

/** What is really going on: a record that says "running" is only true if the backend still has that run. */
function effective(recorded: string, updatedAt: string, thread: ThreadState | null): { status: RunStatus; note: string } {
  const status = (["running", "waiting", "done", "failed", "stopped"].includes(recorded) ? recorded : "running") as RunStatus;
  if (status === "done" || status === "failed" || status === "stopped" || thread === null) return { status, note: "" };
  if (thread === "unreachable") return { status, note: "The research backend is not answering, so this status may be out of date." };
  if (thread === "missing") {
    return { status: "lost", note: "The backend no longer knows this run (it was restarted). What it finished is listed below; start the goal again to continue." };
  }
  if (thread === "error") return { status: "failed", note: "The backend reports this run ended with an error." };
  if (thread === "idle") return { status: "stopped", note: "The run is no longer running (it was stopped or ended without finishing)." };
  if (thread === "interrupted") return { status: "waiting", note: "" };
  // busy: it is running; flag it if nothing has been recorded for a long time
  const age = Date.now() - Date.parse(updatedAt);
  if (Number.isFinite(age) && age > STALL_MS) {
    return { status: "stalled", note: `No progress recorded for ${Math.round(age / 60000)} minutes. A model call may be stuck; you can stop the run.` };
  }
  return { status: "running", note: "" };
}

function summarize(rec: Record<string, unknown>, id: string, thread: ThreadState | null): RunSummary {
  const updatedAt = str(rec.updated_at);
  const eff = effective(str(rec.status), updatedAt, thread);
  return {
    id,
    goal: str(rec.goal),
    status: eff.status,
    recordedStatus: str(rec.status),
    step: str(rec.step),
    waitingFor: typeof rec.waiting_for === "string" ? rec.waiting_for : null,
    startedAt: str(rec.started_at),
    updatedAt,
    progress: (rec.progress && typeof rec.progress === "object" ? rec.progress : {}) as RunProgress,
    reportPath: str(rec.report_path),
    error: str(rec.error),
    note: eff.note,
  };
}

const ACTIVE = new Set(["running", "waiting"]);

export async function listRuns(): Promise<RunSummary[]> {
  const dir = runsDir();
  if (!dir) return [];
  let files: string[] = [];
  try {
    files = (await fs.readdir(dir)).filter((f) => f.endsWith(".json") && !f.endsWith(".evidence.json"));
  } catch {
    return [];
  }
  const runs = await Promise.all(
    files.map(async (f) => {
      const id = f.replace(/\.json$/, "");
      const rec = await readRecord(id);
      if (!rec) return null;
      const thread = ACTIVE.has(str(rec.status)) ? await threadState(id) : null;
      return summarize(rec, id, thread);
    })
  );
  return runs.filter((r): r is RunSummary => r !== null).sort((a, b) => (a.updatedAt < b.updatedAt ? 1 : -1));
}

export async function getRun(id: string): Promise<RunDetail | null> {
  const rec = await readRecord(id);
  if (!rec) return null;
  const thread = ACTIVE.has(str(rec.status)) ? await threadState(id) : null;
  const events = Array.isArray(rec.events) ? (rec.events as RunEvent[]) : [];
  const stats = (rec.stats && typeof rec.stats === "object" ? rec.stats : {}) as Record<string, number>;
  const collected = Array.isArray(rec.collected) ? (rec.collected as CollectedRow[]) : [];
  const sources = Array.isArray(rec.sources) ? (rec.sources as UsedSource[]) : [];
  const goal = str(rec.goal);
  // newer records carry these fields themselves; for the rest, ask the engine what it kept
  const tv = rec.plan && rec.clarify_questions ? null : await threadValues(id);
  const strings = (v: unknown): string[] => (Array.isArray(v) ? v.filter((q): q is string => typeof q === "string") : []);
  const asked = strings(rec.clarify_questions).length > 0 ? strings(rec.clarify_questions) : strings(tv?.questions);
  const fromThread = typeof tv?.clarifications === "string" && tv.clarifications.trim() ? parseAnswerLines(tv.clarifications) : [];
  const answered = Array.isArray(rec.clarifications) ? (rec.clarifications as QA[]).filter((p) => p && typeof p.question === "string") : fromThread.length > 0 ? fromThread : parseClarifications(goal);
  const planRec = (rec.plan && typeof rec.plan === "object" ? rec.plan : null) as Partial<PlanInfo> | null;
  const tvPlan = tv?.plan && typeof tv.plan === "object" ? (tv.plan as { title?: unknown; sub_questions?: unknown; outline?: unknown }) : null;
  const plan: PlanInfo | null =
    planRec && Array.isArray(planRec.questions)
      ? { title: str(planRec.title), questions: planRec.questions.map(String), outline: Array.isArray(planRec.outline) ? planRec.outline.map(String) : [] }
      : tvPlan && Array.isArray(tvPlan.sub_questions)
        ? { title: str(tvPlan.title), questions: tvPlan.sub_questions.map(String), outline: Array.isArray(tvPlan.outline) ? (tvPlan.outline as { title?: unknown }[]).map((o) => str(o?.title)) : [] }
        : questionsFromEvents(events);
  const coverage = Array.isArray(rec.coverage) ? (rec.coverage as CoverageRec[]) : Array.isArray(tv?.coverage) ? (tv.coverage as CoverageRec[]) : [];
  const questionFacts = Array.isArray(rec.question_facts) ? (rec.question_facts as unknown[]).map((n) => (typeof n === "number" ? n : 0)) : [];
  return {
    ...summarize(rec, id, thread),
    clarifyQuestions: asked.length > 0 ? asked : answered.map((p) => p.question),
    clarifications: answered,
    plan,
    coverage,
    questionFacts,
    collected,
    sources,
    events,
    stats,
    backendReachable: thread !== "unreachable",
  };
}

/** Ask the backend to stop the run, and record that the user did. Returns a message for the page. */
export async function stopRun(id: string): Promise<{ ok: boolean; message: string }> {
  if (!validRunId(id)) return { ok: false, message: "Invalid run id" };
  try {
    const list = await fetch(`${UPSTREAM}/threads/${encodeURIComponent(id)}/runs`, {
      cache: "no-store",
      signal: AbortSignal.timeout(3000),
    });
    if (list.ok) {
      const runs = (await list.json()) as { run_id: string; status: string }[];
      await Promise.all(
        runs
          .filter((r) => r.status === "running" || r.status === "pending")
          .map((r) =>
            fetch(`${UPSTREAM}/threads/${encodeURIComponent(id)}/runs/${encodeURIComponent(r.run_id)}/cancel?action=interrupt`, {
              method: "POST",
              signal: AbortSignal.timeout(3000),
            })
          )
      );
    }
  } catch {
    /* the backend may already be gone; the record is still marked stopped below */
  }
  const dir = runsDir();
  const rec = await readRecord(id);
  if (dir && rec && ACTIVE.has(str(rec.status))) {
    const events = Array.isArray(rec.events) ? (rec.events as RunEvent[]) : [];
    events.push({ t: new Date().toISOString(), text: "Stopped from the dashboard" });
    const next = { ...rec, status: "stopped", waiting_for: null, events, updated_at: new Date().toISOString() };
    const file = path.join(dir, `${id}.json`);
    try {
      await fs.writeFile(`${file}.tmp`, JSON.stringify(next, null, 1), "utf-8");
      await fs.rename(`${file}.tmp`, file);
    } catch {
      return { ok: false, message: "Asked the backend to stop, but could not update the run record." };
    }
  }
  return { ok: true, message: "Stop requested." };
}

/** Older run records only keep the answers inside the goal text: "Clarifications from the user:\n<question>\n  -> <answer>". */
export function parseClarifications(goal: string): QA[] {
  const at = goal.indexOf("Clarifications from the user:");
  return at < 0 ? [] : parseAnswerLines(goal.slice(at + "Clarifications from the user:".length));
}

/** "<question>\n  -> <answer>" lines, as the dashboard sends them and the graph keeps them. */
export function parseAnswerLines(text: string): QA[] {
  const out: QA[] = [];
  for (const raw of text.split("\n")) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith("->") && out.length > 0) out[out.length - 1].answer = line.slice(2).trim();
    else out.push({ question: line, answer: "" });
  }
  return out;
}

/** Older records have no plan field, but each answered question left an event: "Q5/7: 6 passages -> <question>". */
export function questionsFromEvents(events: RunEvent[]): PlanInfo | null {
  const qs = new Map<number, string>();
  for (const e of events) {
    const m = /^Q(\d+)\/(\d+):\s*\d+ passages -> (.+)$/.exec(e.text);
    if (m) qs.set(Number(m[1]), m[3]);
  }
  if (qs.size === 0) return null;
  return { title: "", questions: [...qs.entries()].sort((a, b) => a[0] - b[0]).map(([, q]) => q), outline: [] };
}
