// Run with: node --test src/lib/compare.test.ts
import test from "node:test";
import assert from "node:assert/strict";
import { compareIssues, sameTopic, type IssueFacts } from "./compare.ts";
import { parseReport } from "./report.ts";

const issue = (title: string, md: string, facts: number, sources: number): IssueFacts => ({
  title,
  goal: "What do practitioners recommend for chunking?",
  date: "2026-10-01",
  words: 100,
  facts,
  sources,
  report: parseReport(md, title),
});

const EARLY = `# T

## Evidence status

| Section | Facts | Documents | Status |
|---|---|---|---|
| Strategies | 4 | 1 | supported |
| Scale | 0 | 0 | no evidence |

## Strategies

Fixed windows. [E1] [single source]

## Scale

The library does not have enough evidence for this section.

## Practical Recommendations

Use fixed windows of 512 tokens. [single source]

## Sources

- Old blog
- Shared paper
`;

const LATE = `# T

## Evidence status

| Section | Facts | Documents | Status |
|---|---|---|---|
| Strategies | 21 | 4 | supported |
| Scale | 0 | 0 | no evidence |

## Strategies

Structure matters. [E1][E2] [established]

## Scale

The library does not have enough evidence for this section.

## Practical Recommendations

Split on document structure. [established]

## Sources

- Shared paper
- New paper
`;

test("same goal, or mostly the same title words, counts as the same topic", () => {
  assert.ok(sameTopic({ title: "A", goal: "Chunking in RAG?" }, { title: "B", goal: "chunking in rag" }));
  assert.ok(sameTopic({ title: "Chunking Documents in RAG Systems", goal: "" }, { title: "Document Chunking in RAG Systems", goal: "" }));
  assert.ok(!sameTopic({ title: "Chunking in RAG", goal: "x" }, { title: "Serverless pricing", goal: "y" }));
});

test("chapters show more evidence, sources show what arrived, recommendation shows the change", () => {
  const c = compareIssues(issue("T", EARLY, 4, 2), issue("T", LATE, 21, 2));
  const strategies = c.chapters.find((x) => x.title === "Strategies");
  assert.deepEqual([strategies?.before, strategies?.after, strategies?.change], [4, 21, "more"]);
  assert.equal(c.chapters.find((x) => x.title === "Scale")?.change, "same");
  assert.deepEqual(c.addedSources, ["New paper"]);
  assert.deepEqual(c.droppedSources, ["Old blog"]);
  assert.equal(c.recommendation?.changed, true);
  assert.match(c.recommendation?.after ?? "", /document structure/);
  assert.deepEqual(c.stats[0], { label: "Verified facts", before: 4, after: 21 });
});

test("an issue with no recommendations chapter gives no recommendation comparison, and nothing throws", () => {
  const c = compareIssues(issue("T", "# T\n\n## Only\n\nText.\n", 1, 0), issue("T", LATE, 21, 2));
  assert.equal(c.recommendation, null);
  assert.ok(c.chapters.some((x) => x.change === "dropped"));
});
