# Phase 1b: Collecting and reading (collect wide, structured facts, fact bank, chat preview)

**Goal:** a run collects wide and indexes everything it collects; every
fact that leaves the reading stage names its real subject, comes from a
good source, and is stored for reuse, within the run limits. The phase ends
with a chat preview the user can use daily.

**Depends on:** P1a gate. **Task order is set by the P1a-0 error analysis**: the stage with the most errors goes first; a structured stage that does not beat the raw-passage baseline on the scoreboard is cut (S11).
**Scope items:** P1.2 (L2-L6 enforced), P1.5, P1.6, P1.7, P1.8, P1.9, P1.10, P1.22, P1.23, P1.24, P1.25, E-001 (subject part), E-002.

## Tasks

- [ ] Topic collections on top of namespaces; a run is tied to one collection.
- [ ] Collect wide (SCOPE section 5): remove the 40-candidate / 8-per-question discovery cap; plan approval carries the collection rules (source types, sites, date range); the candidate list becomes an optional exclude list; L2 safety cap.
- [ ] Every collected source is indexed into the run's collection; run record counts found / collected / indexed / read / used.
- [ ] Source states (`indexed` / `read` / `used`) and origin (`web` / `upload`) stored per source and shown in Library.
- [ ] Ranking for reading per question: relevance + tier + novelty, within L3/L4; the rest stays `indexed`.
- [ ] Source tiers stored per document (paper > docs/primary > model card > blog > aggregator), shown in Library.
- [ ] Version merge and dedupe (arXiv v1/v2, abs/pdf, repeated pages).
- [ ] Reading as a **subgraph** per question, fanned out with **Send**, `max_concurrency=1`, selection node `defer=True`.
- [ ] Structured fact extraction (core + AI/ML fields) via schema-constrained output.
- [ ] Subject check by field comparison; on mismatch rewrite to the source's terms or drop (logged).
- [ ] Fact bank tables (same SQLite DB as the library) with provenance: source, passage, run, model, prompt version.
- [ ] **CachePolicy** on extraction/verification keyed by (passage hash, question, model, prompt version).
- [ ] **RetryPolicy**: connection errors retried, timeouts not.
- [ ] Limits L3-L6 enforced; read / set-aside lists recorded.
- [ ] Trace and fix garbled characters (E-002).

### Chat preview (last task of 1b)
- [ ] One chat function over a collection: hybrid search of passages + fact bank → answer with citations, using an installed model (gemma4:e4b; research model unloaded).
- [ ] Answers say which evidence is checked (fact bank) and which is unchecked (passage only); refuse when retrieval finds nothing relevant.
- [ ] Minimal dashboard page (question box, answer, clickable sources); no threads, no agent loop, no report hand-off (those are Phase 2).
- [ ] The user uses it for a week; problems go to the Phase 2 doc as inputs.

## Test cases

| ID | Type | Case | Expected |
|---|---|---|---|
| P1b-T01 | Unit | Passage about a 17B model, question about 4B pretraining (E79) | Fact `size=17B`; claim may not say 4B; dropped or rewritten |
| P1b-T02 | Unit | Post-training paper, question about pretraining (E7/E8) | `stage=post-training`; not usable as pretraining evidence |
| P1b-T03 | Unit | Fine-tuned model card (E76/E40) | `stage=fine-tuning`; correct subject |
| P1b-T04 | Golden | 30-fact sample from the saved SLM run | 0 subject violations (manual check) |
| P1b-T05 | Unit | arXiv v1 + v2 + abs page of one paper | One source |
| P1b-T06 | Unit | Tier assignment for paper, model card, blog, aggregator | Correct tier each |
| P1b-T07 | Integration | 4 questions via Send; crash after question 2; resume | Questions 1-2 not re-read; 3-4 read |
| P1b-T08 | Integration | Same run twice | Second run's extraction served from cache (no model calls for cached passages) |
| P1b-T09 | Budget | 20 candidate sources for one question, L3=12 | 12 read; 8 listed as set aside with reasons |
| P1b-T10 | Unit | One source with 9 good facts, L6=4 | 4 kept, best by relevance/novelty |
| P1b-T11 | Unit | Fact bank row | All core + pack fields + provenance present |
| P1b-T12 | Adversarial | PDF with bad encoding | No `�` in stored text/titles, or document flagged |
| P1b-T13 | Unit | Collection isolation | A run on collection A never retrieves from B |
| P1b-T14 | Unit | Ollama connection refused once vs timeout | Connection retried; timeout not retried, reported |
| P1b-T15 | Integration | Discovery finds 150 sources for 4 questions, L2=300 | All 150 collected and indexed without ticking; excluded ones skipped |
| P1b-T16 | Integration | Same run, L4=50 | 50 read, the rest stay `indexed` and are searchable; run record counts match |
| P1b-T17 | Budget | 400 found, L2=300 | 300 collected (best ranked first); 100 listed as not collected with the reason |
| P1b-T18 | Unit | Source state transitions | `indexed` → `read` → `used`; never backwards; origin set on every source |
| P1b-T19 | Unit | Ranking for reading | Higher tier and more relevant first; near-duplicate of an already-read source ranked down |
| P1b-T20 | Golden | Chat preview: 10 questions over the SLM collection | Every answer cited; unchecked evidence marked; numbers present in the cited passage or fact |
| P1b-T21 | Adversarial | Chat preview: 2 questions the library cannot answer | Refuses; no answer from general knowledge |

## Review items
- Subject check compares fields; no prose-similarity heuristics.
- Fact bank schema reviewed against SCOPE section 6 and Phase 2/3 needs (chat search, reuse).

## Exit gate
- [ ] All test cases pass; full offline suite green; P1b-T04 at 0 violations.
- [ ] Chat preview in daily use; findings written into the Phase 2 doc.
- [ ] Scoreboard column "P1b" filled; subject accuracy beats the raw-passage baseline.
- [ ] No open Critical/High errors for P1b; E-001 subject part closed; E-002 closed.

## Results
_Fill in at the gate._
