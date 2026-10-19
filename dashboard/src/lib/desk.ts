import fs from "node:fs";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";

// The Research Desk database (<vault>/.desk/desk.sqlite). The Python graph writes each run's trace into it
// (src/research_assistant/desk.py); this module reads that trace and WRITES FEEDBACK, the only thing the dashboard writes.
// Both sides apply the one schema file, src/research_assistant/desk_schema.sql, so they cannot drift apart.
const VAULT_PATH = process.env.VAULT_PATH ?? "";
const ROOT = process.env.RESEARCH_ROOT || path.resolve(process.cwd(), "..");
const SCHEMA = path.join(ROOT, "src", "research_assistant", "desk_schema.sql");

export type Target = "report" | "section" | "sentence" | "chunk";
export type Rating = "relevant" | "not_relevant" | "wrong_subject" | "wrong" | "helpful" | "partly" | "not_helpful" | "cleared";

/** Which ratings each kind of target accepts ("cleared" withdraws an earlier rating). */
export const RATINGS: Record<Target, Rating[]> = {
  chunk: ["relevant", "not_relevant", "wrong_subject", "cleared"],
  sentence: ["wrong", "cleared"],
  section: ["helpful", "not_helpful", "cleared"],
  report: ["helpful", "partly", "not_helpful", "cleared"],
};

export interface FeedbackInput {
  runId: string;
  reportSlug?: string;
  target: Target;
  targetRef: string;
  rating: Rating;
  reason?: string;
  section?: string;
}

export interface RunView {
  runId: string;
  engine: string;
  model: string;
  /** E-number -> the library chunk behind it. */
  evidence: Record<string, { chunkId: number | null; docTitle: string; heading: string; url: string }>;
  /** Section title -> its sentences in order. */
  sentences: Record<string, { key: string; text: string; cites: string[]; flag: string }[]>;
  /** "target|ref" -> the latest rating (and reason) that was not withdrawn. */
  feedback: Record<string, { rating: Rating; reason: string }>;
}

export function deskPath(): string {
  return VAULT_PATH ? path.join(VAULT_PATH, ".desk", "desk.sqlite") : "";
}

let ready = "";

function open(): DatabaseSync | null {
  const p = deskPath();
  if (!p) return null;
  fs.mkdirSync(path.dirname(p), { recursive: true });
  const db = new DatabaseSync(p);
  db.exec("PRAGMA busy_timeout=10000");
  if (ready !== p || !fs.existsSync(p)) {
    db.exec("PRAGMA journal_mode=WAL");
    db.exec(fs.readFileSync(SCHEMA, "utf-8"));
    ready = p;
  }
  return db;
}

export function validFeedback(x: unknown): x is FeedbackInput {
  if (!x || typeof x !== "object") return false;
  const f = x as Record<string, unknown>;
  const target = f.target as Target;
  return (
    typeof f.runId === "string" &&
    /^[\w.-]{1,80}$/.test(f.runId) &&
    typeof f.targetRef === "string" &&
    f.targetRef.length > 0 &&
    f.targetRef.length <= 400 &&
    target in RATINGS &&
    RATINGS[target].includes(f.rating as Rating) &&
    (f.reason === undefined || typeof f.reason === "string") &&
    (f.section === undefined || typeof f.section === "string") &&
    (f.reportSlug === undefined || (typeof f.reportSlug === "string" && /^[\w.-]*$/.test(f.reportSlug)))
  );
}

/** Store one click. Append-only: the latest row per target wins. Chunk feedback is tied to the exact library chunk
 *  (id, and a text hash that survives a library rebuild) and every row to the engine version that produced it. */
export function saveDeskFeedback(f: FeedbackInput): number | null {
  const db = open();
  if (!db) return null;
  try {
    const run = db.prepare("SELECT engine FROM runs WHERE run_id = ?").get(f.runId) as { engine?: string } | undefined;
    const ev =
      f.target === "chunk"
        ? (db.prepare("SELECT chunk_id, text_hash, doc_title FROM evidence WHERE run_id = ? AND eid = ?").get(f.runId, f.targetRef) as
            | { chunk_id: number | null; text_hash: string; doc_title: string }
            | undefined)
        : undefined;
    const sentence =
      f.target === "sentence"
        ? (db.prepare("SELECT section FROM sentences WHERE run_id = ? AND sentence_key = ?").get(f.runId, f.targetRef) as
            | { section: string }
            | undefined)
        : undefined;
    const res = db
      .prepare(
        "INSERT INTO feedback (created_at, run_id, engine, report_slug, target, target_ref, rating, reason, section, eid, " +
          "chunk_id, text_hash, doc_title) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
      )
      .run(
        new Date().toISOString(),
        f.runId,
        run?.engine ?? "",
        f.reportSlug ?? "",
        f.target,
        f.targetRef,
        f.rating,
        (f.reason ?? "").slice(0, 1000),
        f.section ?? sentence?.section ?? "",
        f.target === "chunk" ? f.targetRef : "",
        ev?.chunk_id ?? null,
        ev?.text_hash ?? "",
        ev?.doc_title ?? "",
      );
    return Number(res.lastInsertRowid);
  } finally {
    db.close();
  }
}

/** What the report page needs from the trace: evidence -> chunk, sentences per section, and the current feedback. */
export function runView(runId: string): RunView | null {
  const db = open();
  if (!db) return null;
  try {
    const run = db.prepare("SELECT engine, model FROM runs WHERE run_id = ?").get(runId) as { engine: string; model: string } | undefined;
    if (!run) return null;
    const evidence: RunView["evidence"] = {};
    for (const r of db.prepare("SELECT eid, chunk_id, doc_title, heading, url FROM evidence WHERE run_id = ?").all(runId) as {
      eid: string;
      chunk_id: number | null;
      doc_title: string;
      heading: string;
      url: string;
    }[]) {
      evidence[r.eid] = { chunkId: r.chunk_id, docTitle: r.doc_title, heading: r.heading, url: r.url };
    }
    const sentences: RunView["sentences"] = {};
    for (const r of db
      .prepare("SELECT section, sentence_key, text, cites, flag FROM sentences WHERE run_id = ? ORDER BY section, position")
      .all(runId) as { section: string; sentence_key: string; text: string; cites: string; flag: string }[]) {
      (sentences[r.section] ??= []).push({ key: r.sentence_key, text: r.text, cites: JSON.parse(r.cites) as string[], flag: r.flag });
    }
    const feedback: RunView["feedback"] = {};
    for (const r of db
      .prepare("SELECT target, target_ref, rating, reason FROM feedback WHERE run_id = ? ORDER BY id")
      .all(runId) as { target: string; target_ref: string; rating: Rating; reason: string }[]) {
      const key = `${r.target}|${r.target_ref}`;
      if (r.rating === "cleared") delete feedback[key];
      else feedback[key] = { rating: r.rating, reason: r.reason };
    }
    return { runId, engine: run.engine, model: run.model, evidence, sentences, feedback };
  } finally {
    db.close();
  }
}
