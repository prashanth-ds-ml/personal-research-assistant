// Run with: node --test src/lib/desk.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";

const vault = fs.mkdtempSync(path.join(os.tmpdir(), "desk-"));
process.env.VAULT_PATH = vault;
process.env.RESEARCH_ROOT = path.resolve(import.meta.dirname, "..", "..", "..");
const desk = await import("./desk.ts");

function seed() {
  const db = new DatabaseSync(desk.deskPath());
  db.exec("INSERT INTO runs (run_id, engine, model, started_at) VALUES ('r1', 'v3.0-hybrid', 'qwen3.5:4b', 't')");
  db.exec("INSERT INTO evidence (run_id, eid, chunk_id, text_hash, doc_title) VALUES ('r1', 'E1', 42, 'abc', 'Paper A')");
  db.exec("INSERT INTO sentences (run_id, section, position, sentence_key, text, cites, flag) VALUES " +
          "('r1', 'Setup', 1, 'k1', 'Qwen3-4B was used [E1].', '[\"E1\"]', 'subject')");
  db.close();
}

test("feedback is validated per target before it is stored", () => {
  assert.equal(desk.validFeedback({ runId: "r1", target: "chunk", targetRef: "E1", rating: "relevant" }), true);
  assert.equal(desk.validFeedback({ runId: "r1", target: "chunk", targetRef: "E1", rating: "helpful" }), false);   // not a chunk rating
  assert.equal(desk.validFeedback({ runId: "r1", target: "page", targetRef: "E1", rating: "relevant" }), false);
  assert.equal(desk.validFeedback({ runId: "../x", target: "chunk", targetRef: "E1", rating: "relevant" }), false);
  assert.equal(desk.validFeedback({ runId: "r1", target: "sentence", targetRef: "", rating: "wrong" }), false);
});

test("chunk feedback is tied to the library chunk and the engine; the latest rating wins; cleared withdraws", () => {
  assert.equal(desk.runView("nope"), null);                 // also creates the database with the shared schema
  seed();
  desk.saveDeskFeedback({ runId: "r1", target: "chunk", targetRef: "E1", rating: "relevant", section: "Setup" });
  desk.saveDeskFeedback({ runId: "r1", target: "chunk", targetRef: "E1", rating: "wrong_subject" });
  desk.saveDeskFeedback({ runId: "r1", target: "sentence", targetRef: "k1", rating: "wrong", reason: "4B is not in E1" });
  desk.saveDeskFeedback({ runId: "r1", target: "report", targetRef: "slug", rating: "partly" });
  desk.saveDeskFeedback({ runId: "r1", target: "report", targetRef: "slug", rating: "cleared" });

  const v = desk.runView("r1");
  assert.ok(v);
  assert.equal(v.engine, "v3.0-hybrid");
  assert.deepEqual(v.feedback["chunk|E1"], { rating: "wrong_subject", reason: "" });
  assert.deepEqual(v.feedback["sentence|k1"], { rating: "wrong", reason: "4B is not in E1" });
  assert.equal(v.feedback["report|slug"], undefined);
  assert.deepEqual(v.sentences.Setup[0], { key: "k1", text: "Qwen3-4B was used [E1].", cites: ["E1"], flag: "subject" });

  const db = new DatabaseSync(desk.deskPath());
  const rows = db.prepare("SELECT target, rating, engine, chunk_id, text_hash, doc_title, section FROM feedback ORDER BY id").all();
  db.close();
  assert.equal(rows.length, 5);                              // append-only: every click is kept
  assert.deepEqual({ ...rows[1] }, { target: "chunk", rating: "wrong_subject", engine: "v3.0-hybrid", chunk_id: 42, text_hash: "abc", doc_title: "Paper A", section: "" });
  assert.equal(rows[2].section, "Setup");                    // a sentence's section comes from the trace
});
