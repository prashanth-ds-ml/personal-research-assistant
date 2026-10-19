// Run with: node --test src/lib/runs.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { parseClarifications, questionsFromEvents } from "./runs.ts";

test("answers are recovered from the goal text of an older run record", () => {
  const goal = "What is RRF?\n\nClarifications from the user:\nWhich part matters most?\n  -> Strategy, then quality\nWhat documents?\n  -> Mostly PDFs";
  assert.deepEqual(parseClarifications(goal), [
    { question: "Which part matters most?", answer: "Strategy, then quality" },
    { question: "What documents?", answer: "Mostly PDFs" },
  ]);
});

test("a goal with no clarifications gives none", () => {
  assert.deepEqual(parseClarifications("Just a goal"), []);
});

test("a question that was skipped has an empty answer", () => {
  const out = parseClarifications("g\n\nClarifications from the user:\nQ1?\nQ2?\n  -> yes");
  assert.deepEqual(out, [{ question: "Q1?", answer: "" }, { question: "Q2?", answer: "yes" }]);
});

test("plan questions are recovered from the progress events of an older run", () => {
  const events = [
    { t: "1", text: "Library: 110 documents" },
    { t: "2", text: "Q2/3: 6 passages -> How do rankings fuse?" },
    { t: "3", text: "Q1/3: 8 passages -> What is RRF?" },
  ];
  assert.deepEqual(questionsFromEvents(events)?.questions, ["What is RRF?", "How do rankings fuse?"]);
  assert.equal(questionsFromEvents([{ t: "1", text: "nothing" }]), null);
});
