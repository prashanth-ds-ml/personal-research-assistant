# Research Desk: scope v3

**Version:** 3.0 · **Agreed:** 2026-10-19 · **Replaces:** v2.2 (`SCOPE-v2.2-2026-10-19.md`, plan docs in `archive/v2.2/`)
**Why v3:** v2.2 buried a simple idea under process (12 sprints, labelling, judge calibration). v3 keeps the idea and cuts the rest.

## The product in one line

**Deep research that builds your private library, plus chat over that library, with your feedback improving both.**
Runs on one laptop, one local model, no cloud.

- **Primary: deep research.** Goal → sub-questions you approve → web search → collect PDFs/pages → index everything →
  a short report, every sentence cited to a source passage, gaps stated.
- **Secondary: chat** over the same library, same engine. When the library cannot answer, it offers to start research.
- **Feedback loop:** sources and answers are shown with one-click feedback; feedback becomes the test set and the
  case-study numbers.
- **Used daily by the builder from the first milestone.** Real use is the evaluation.

## The engine

```
collect (web + PDFs) → library: chunks + BM25 (FTS5) + vectors        [built]
                          ↓
      retrieve: hybrid (RRF) top ~30 → reranker → best 6-8 chunks      [built; reranker on, M3]
      each chunk carries [document title › section heading]
             ↓                                   ↓
   Report: one section per sub-question,     Chat: answer from chunks,
   written from its own chunks               cite them
```

The fact-extraction step and the LLM judge are **removed**: the writer reads the chunks themselves. (E-001: the paraphrased
"fact" took the question's subject; v1 got the subject right in 22 of 42 checked facts.)

## Models

| Role | Model | Notes |
|---|---|---|
| Plan, write, chat (the only LLM) | `qwen3.5:4b` | 3.4 GB, fits the 8 GB GPU; context 16k; *Think when writing* ON by default (~90 s per section, 92% clean sentences); *Think when planning* optional, off |
| Embeddings | `qwen3-embedding:0.6b` | unchanged (library built with it) |
| Reranker (M3) | `bge-reranker-v2-m3` (multilingual) | on the CPU via transformers; ON by default (offline top-3 88% -> 100%) |

One setting changes the LLM; a better model replaces it when feedback says so.

## Chunking (locked 2026-10-19)

Every document is cut the same way: text chunks up to 1,800 characters, tables up to 3,000 (split by rows, header kept but
capped), heading path up to 300 characters. The library records `v2 text=1800 table=3000` and refuses to mix; a change
needs a full re-chunk (`scripts/reindex.py --rebuild`, ~5 minutes, no PDF conversion). Chosen by Test A: 1,400-2,500
characters sit on the same retrieval plateau; 600-1,000 are clearly worse at ranking the right chunk first.

## Report rules (no-hallucination design)

1. **Section = one sub-question = its own 6-8 chunks.** Every sentence cites a chunk `[C3]`. If the chunks do not answer,
   the section says so in one line (a gap), not a padded paragraph.
2. **Length follows evidence:** 400-600 words per section (Test D: accurate up to ~600, padding from ~800), at most 8
   passages per section (Test C); a report is ~1,000-3,000 words of cited text (v2 reports were 4,700-6,900).
3. **Context budget per section** (16k window): instructions ~700 tokens + 8 chunks × ~450 + output ~600 ≈ 5k tokens.
   Nothing is clipped silently; any cut is logged.
4. **Summary only from section sentences,** with their citations: the recommendation plus each section's first cited
   sentence, copied (built 2026-10-19). No new claims in the summary: no place to stitch.
5. **Code checks on every cited sentence** (no extra LLM): numbers must appear in the cited chunk; model names/sizes must
   appear in the chunk or its document title; citations must point to real chunks; a sentence whose words are barely in
   its cited chunk is flagged; a citation that another chunk of the section clearly carries better is moved there
   (citation repair). Tables must cite every row. A failing sentence is flagged in the report.
6. Errors cannot be guaranteed away; every claim is short, cited, checkable and visible, and the reader can flag it.

## Feedback

| Where | Feedback |
|---|---|
| Each source chunk under a section or chat answer | 👍 relevant · 👎 not relevant · ⚠ wrong subject |
| Each sentence (optional) | 🚩 wrong + short reason |
| Whole report / answer | helpful: yes · partly · no + optional comment |

Stored in the **desk database** (`<vault>/.desk/desk.sqlite`, schema `src/research_assistant/desk_schema.sql`), kept apart
from the library database because that one is rebuilt on re-embedding. Every click is a row (append-only, latest wins) tied
to the run, the exact library chunk (id + text hash) and the **engine version** (`v3.0-hybrid`, `v3.1-rerank`, ...). The same
database holds each run's **trace**: steps, model calls, retrieved chunks with their ranks, relevance grades, what each
section's writer saw, and every report sentence with its citations and flags. Uses: (1) rated chunks become retrieval regression tests; (2) flagged sources are demoted for that
goal; (3) later, with a few hundred labels, tuning of weights and reranker. No automatic retraining.

## Milestones

| # | What | Done when |
|---|---|---|
| M1 | **Research from chunks**, one model: research step retrieves chunks (hybrid) instead of extracting facts; writer per the report rules; code checks; engine version in the run record | Claude: tests + one live run on a small goal. You: run one real goal and read the report |
| M2 | **Source panel + feedback** on reports (dashboard), feedback table, versions | You rate the sources of a report in under 2 minutes. **Baseline period starts: use it daily** |
| M3 | **Reranker:** measured on the frozen retrieval set (hybrid vs hybrid + rerank); switched on as `v3.1` if it wins | Offline recall numbers in EVALS; before/after on your ratings after a few days |
| M4 | **Chat** over the library: same retrieve → rerank → answer, same source panel and feedback, "research this" when the library has no answer | You use chat for your own questions for a week |
| M5 | **Insights page** (questions, % sources relevant, helpful rate, worst sources, per version) + demo polish + README + case study numbers | A 10-minute client demo works end to end |

## Kept from v2

Collection pipeline (discover → review → collect, Docling), plan approval and coverage check, the library (hybrid search,
measured 80/88/96% recall at 1/3/6), dashboard, run records, Stop/resume, tests, ERROR_LOG, DECISIONS, EVALS, CASE_STUDY.

## Dropped

Fact extraction + LLM judge, the 50-claim labelling sheet and judge calibration (feedback replaces them), the four source
levels and fact bank, critique/revise, the multi-model bake-off as a gate, 12-sprint plan and user-test list.
The Phase 1a-0 tooling stays in the repo (eval_tools, frozen retrieval set) where it is still useful.

## Testing

- **Claude:** pytest for every change (named by milestone, e.g. `M1_T03`), live runs on a small goal, dashboard checks,
  secret scan before any publish.
- **You:** use it and give feedback. Nothing else is required of you.
- **Evals (EVALS.md):** frozen retrieval set, code-check pass rate per report, feedback metrics per engine version.

## Not now

Cloud models, multiple users, fine-tuning, bank/intranet portals (feasible later), a second domain, v1 quick-research mode
(keep/archive decided at M5).
