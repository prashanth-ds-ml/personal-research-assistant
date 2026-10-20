// Run with: node --test src/lib/report.test.ts   (Node 22+ strips the types itself; no extra tooling)
import test from "node:test";
import assert from "node:assert/strict";
import { countLabels, markCites, parseReport, readMinutes } from "./report.ts";

const SAMPLE = `# Practical Guidance on Chunking

> **Goal:** What do practitioners recommend for chunking? Clarifications from the user: none

## Evidence status

| Section | Facts | Documents | Status |
|---|---|---|---|
| Chunking Strategies | 21 | 4 | supported |
| Scalability | 0 | 0 | no evidence found |

## Executive summary

Structure-aware chunks retrieve better. [E3] [established]

## Chunking Strategies

Fixed windows cut tables in half. [E3][E8] [established] Size trades recall for noise. [single source]

## Scalability

The library does not have enough evidence for this section. [inference]

## Limitations

- Written by a small local model.
- Every sentence is labelled.

## Sources

### Papers and PDFs (2)

- [Adaptive Chunking](http://arxiv.org/abs/2603.25333v1) - 22 fact(s), 0 cited
- Survey of RAG - 9 fact(s), 0 cited

### Web pages (1)

- [A blog](https://example.org/post) - 3 fact(s), 0 cited

## Evidence appendix

| ID | Claim | Verbatim quote | Source |
|---|---|---|---|
| E3 | Fixed splitting ignores structure. | "Fixed-size splitting ignores document structure." | Adaptive Chunking |
| E8 | Tables split \\| badly. | "Definitions are separated from terms." | Adaptive Chunking |
`;

test("parses title, goal and evidence status", () => {
  const r = parseReport(SAMPLE);
  assert.equal(r.title, "Practical Guidance on Chunking");
  assert.equal(r.goal, "What do practitioners recommend for chunking?");
  assert.deepEqual(r.status[0], { section: "Chunking Strategies", facts: 21, docs: 4, status: "supported" });
});

test("chapters skip the meta sections and carry their evidence", () => {
  const r = parseReport(SAMPLE);
  assert.deepEqual(r.chapters.map((c) => c.title), ["Chunking Strategies", "Scalability"]);
  assert.equal(r.chapters[0].num, "I");
  assert.deepEqual(r.chapters[0].cites, ["E3", "E8"]);
  assert.equal(r.chapters[0].facts, 21);
  assert.equal(r.chapters[1].kind, "gap");
  assert.equal(r.chapters[1].facts, 0);
});

test("a section the model failed to write is marked failed", () => {
  const r = parseReport("# T\n\n## A\n\n*The model failed to write this section; the supporting evidence is listed in the appendix.* [inference]\n");
  assert.equal(r.chapters[0].kind, "failed");
});

test("sources are grouped and the appendix quotes are read, including escaped pipes", () => {
  const r = parseReport(SAMPLE);
  assert.equal(r.sources.length, 3);
  assert.deepEqual(r.sources.map((s) => s.group), ["pdf", "pdf", "web"]);
  assert.equal(r.sources[0].url, "http://arxiv.org/abs/2603.25333v1");
  assert.equal(r.sources[1].url, "");
  assert.equal(r.evidence.E3.quote, "Fixed-size splitting ignores document structure.");
  assert.equal(r.evidence.E8.claim, "Tables split | badly.");
});

test("older reports with a plain bullet list of sources still parse", () => {
  const r = parseReport("# T\n\n## Sources\n\n- 02-pinecone-io\n- [A paper](http://a.b/c)\n");
  assert.deepEqual(r.sources.map((s) => [s.title, s.url, s.facts]), [["02-pinecone-io", "", 0], ["A paper", "http://a.b/c", 0]]);
});

test("label counts treat every flavour of unsupported as inference", () => {
  const c = countLabels("a [established] b [single source] c [inference] d [inference: figures not from sources] e [cited; figure not in the cited evidence]");
  assert.deepEqual(c, { established: 1, "single source": 1, inference: 3 });
});

test("markCites links cites and labels but leaves real links alone", () => {
  const out = markCites("see [E3] [established] and [a link](http://x.y) [inference: figures not from sources]");
  assert.match(out, /\[E3\]\(#cite-E3\)/);
  assert.match(out, /\[established\]\(#label-established\)/);
  assert.match(out, /\[a link\]\(http:\/\/x\.y\)/);
  assert.match(out, /\(#label-inference\)/);
});

test("never throws on junk and reads minutes sensibly", () => {
  const r = parseReport("not a report at all");
  assert.equal(r.chapters.length, 0);
  assert.equal(readMinutes(0), 1);
  assert.equal(readMinutes(3300), 15);
});

test("markCites turns the v3 check flags into flag tags", () => {
  const out = markCites("A 4B model [E2]. [cited; subject not in the cited evidence] It used 18T [E1]. [cited; figure not in the cited evidence]");
  assert.match(out, /\[check subject\]\(#label-flag\)/);
  assert.match(out, /\[check figure\]\(#label-flag\)/);
  assert.equal(countLabels("x [cited; subject not in the cited evidence] y [inference]").inference, 2);
  assert.match(markCites("z [E3] [cited; wording not found in the cited evidence]."), /\[check wording\]\(#label-flag\)\./);
  assert.match(markCites("y [E4] [cited; domain not stated from the cited evidence]."), /\[check domain\]\(#label-flag\)\./);
});
