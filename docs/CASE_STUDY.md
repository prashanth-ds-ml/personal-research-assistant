# Case study: a local research assistant that shows its work

> **Living document.** Updated at every milestone (progress log at the
> bottom) and rewritten into its final form at v1.0. Every number links to
> `EVALS.md`, `BENCHMARKS.md` or a run record; every lesson links to its
> `DECISIONS.md` or `ERROR_LOG.md` entry. Nothing here is claimed without
> evidence.

## TL;DR

_Written at v1.0._ Draft: a research assistant that runs entirely on one
laptop (8 GB GPU, 24 GB RAM, Ollama, no cloud), builds a knowledge base you
own, and writes reports where every claim opens its source quote in one click.
The interesting part is not the agent: it is how its failures were found,
measured and fixed.

## 1. The problem

Deep-research agents produce confident, fluent reports. Reading them closely,
a share of the claims are wrong in ways a quote check does not catch: the
quote is real, but the claim describes a different model, a different size or
a different training stage than the source. For a team deciding something
real, that is worse than no report.

Constraints chosen on purpose:
- **Private:** runs locally, no paid APIs, documents never leave the machine.
- **Ordinary hardware:** RTX 5050 laptop GPU (8 GB), 23.6 GB RAM.
- **Quality over speed:** a report may take hours; a wrong claim may not pass.

Target user: first the builder (daily AI/ML research), then clients who need
private research over their own documents plus the web.

## 2. Timeline

| Date | Stage | What happened |
|---|---|---|
| 2026-09-29 | Fork | Started from `langchain-ai/local-deep-researcher`; vault-integrated backend, Next.js dashboard, CI |
| 2026-09-29 → 10-01 | v1 build | Deep research graph: clarify, plan, coverage check, collector, evidence gate, claim labels, run records, Stop; 285 offline tests |
| 2026-10-01 | Close-out review | Stuck-call hang, power-capped GPU, shared global state, dead-Ollama silent pass found |
| 2026-10-03 | Report review | **E-001**: claims take the question's subject, not the source's (section 4) |
| 2026-10-12 | Scope v2 | Narrowed: quality first, one stronger model, structured facts, fact bank, chat later |
| 2026-10-18 | Scope v2.1 | Collect wide, index everything, read the best, use a few; chat preview early |
| 2026-10-19 | Scope v2.2 | Measure first: error analysis, simplest baseline, fast dev loop, claim check view |
| 2026-10-19 | **Scope v3** | Back to the core idea: write from reranked chunks (no fact rewriting), one 4B model, feedback loop from daily use; research primary, chat secondary |

## 3. Architecture

_Diagram added at M5._ In words: a LangGraph research graph (goal → clarify →
plan → coverage → collect → index → per sub-question: hybrid retrieve →
rerank → write the section from its chunks → code checks → report) over a
local library (SQLite: documents, chunks with FTS5 + vectors, feedback).
Chat uses the same retrieve → rerank → answer path. One local LLM
(`qwen3.5:4b`) plus small embedding and reranker models.

## 4. The failure that shaped the project (E-001)

A v1 report on "should we pretrain a small model or fine-tune one?" contained:
- "Optimal hyperparameters for **pretraining** a 4B model from scratch",
  taken from a **post-training** evaluation paper (E7/E8).
- "**Pretraining a 4B** model … 22.63T tokens", taken from a **17B** model
  card (E79).
- A summary sentence stitching numbers from four sources, labelled
  **established**.

Every quote was verbatim, so every check passed. The root cause: extraction
phrased facts in the *question's* terms, and the checks tested form (is the
quote real?) not meaning (is the subject the same?).

Fix (v3, M1): remove the paraphrase step. The writer reads the source chunks
themselves, each labelled with its document title and heading, so the subject
is in front of it; code checks that every number and model name in a sentence
appears in the chunk it cites. (v2.2 had planned structured fact fields
instead: more machinery around the step that caused the error.)

**Lesson:** a check must test meaning, not only form. (ERROR_LOG E-001)

## 5. Other lessons, each from a real failure

| Lesson | What happened | Source |
|---|---|---|
| A verifier needs its own positive and negative test | The faithfulness judge rejected everything because of contradictory prompt rules; a full run produced 0 evidence | DECISIONS "The faithfulness judge was broken by my own prompt" |
| Retrieval failures hide as writing failures | A section kept being wrong after prompt fixes; the retriever never found the right paper. Found by reading retrieved passages, not the report | DECISIONS "Retrieval failures hide as writing failures" |
| A streaming call never times out | One model call generated ~79k tokens for 1.5 h; the HTTP read timeout resets on every token | DECISIONS "A streaming model call can never time out" |
| Check the machine before blaming the model | Runs were 5-10× slow: the GPU was capped at 10 W, not a memory problem | DECISIONS "The slowdown was mostly a power-capped GPU" |
| Dependencies change under you | Search returned nothing, silently: the package had been renamed upstream | DECISIONS "The search backend was silently broken" |
| Measure model choices on your own prompts | The tutorial's suggested model was not the fastest; the original default was the slowest of seven | BENCHMARKS.md |

## 6. Key decisions and trade-offs

| Decision | Alternatives rejected | Why |
|---|---|---|
| The model's context bounds a report, not the number of documents | "Read every PDF" | The decision step only ever saw ~24 compressed sentences; compression is where subjects got lost |
| Collect wide, read the best, keep the rest searchable | Tick ~100 candidates by hand | Doesn't scale to hundreds; unread sources still feed chat and later runs |
| One mid-size MoE model (candidate `gemma4:26b-a4b`), confirmed by test | Max context; several small models | Fits 8 GB GPU + RAM; one model loaded at a time |
| Measure first: error analysis by stage, raw-passage baseline | Fix by diagnosis | Effort goes where errors are; complexity must beat the simple thing |
| Rules in code (provenance, labels, gaps) | Trust a bigger model | A bigger model errs less, not never |
| Write from reranked chunks (v3) | Extract facts, then write from facts | The paraphrase step was where subjects got lost (22/42 right); retrieval was already good (96% recall@6) |
| One 4B model for plan, write and chat (v3) | Planner/extractor + separate writer | With extraction gone only light jobs remain; no model swapping on a memory-short laptop |
| Feedback from daily use as the evaluation (v3) | 50-claim labelling sheet, judge calibration | Labels arrive as a side effect of using it; before/after numbers from real use |

## 7. Measurements

_Filled from the scoreboard in `EVALS.md` at each gate._

| Metric | v2 (facts) | v3.0 hybrid | v3.1 rerank |
|---|---|---|---|
| Retrieval recall@1/3/6 (frozen set) | 80/88/96% | 80/88/96% | — |
| Sources rated relevant (your feedback) | — | — | — |
| Reports/answers rated helpful | — | — | — |
| Sentences failing code checks | — | — | — |
| Retrieval at the locked chunk size (top 1/3/6) | 80/88/96% | 80/88/96% | — |
| Words per report (body) | ~4,000 | 1,289 | — |
| Minutes per report (library only) | hours | 3.8 | — |
| Wrong-subject claims found on reading (same goal) | several | 0 | — |

## 8. What I would do differently

_Collected as we go; finalised at v1.0._
- Start with error analysis and a simple baseline before adding pipeline stages (adopted late, in v2.2).
- Build the fast dev loop (saved evidence, mini fixture) before the first multi-hour run.
- Watch for process outgrowing the product: by v2.2 the plan had 12 sprints and a labelling job before
  anything new could be used. v3 put daily use first and let feedback be the measurement.

## 9. What's next

M1 research from chunks → M2 source panel + feedback (daily use starts) →
M3 reranker (before/after) → M4 chat → M5 insights page and client demo
(private documents plus the web, on the client's machine).

---

## Progress log

One entry per sprint (v2.2) or milestone (v3): what was built, what the tests showed, what surprised us, links.

| Step | Dates | Built | Tests (auto / manual) | Finding or surprise | Links |
|---|---|---|---|---|---|
| — | 2026-10-12 → 10-19 | Scope v2 → v2.2, process docs, build order | 328 offline + 19 dashboard pass | Free RAM stays ~5 GB even after a reboot; blocks the model test | DECISIONS scope entries |
| 0 | 2026-10-19 | Reviewed + committed the October fixes (plans stay on the goal, fetcher back-off), docs, dashboard snapshot; branch per phase | 🤖 328 pytest, ruff, 19 dashboard, tsc, eslint, secret scan · 🧑 U-01 pass | The review found prompt examples copied from the one test goal (E-010): a prompt fix tuned on the failing case can flatter the eval. Added a held-out goal to Sprint 1 | ERROR_LOG E-008..E-012; commits fb0d896, 4c9b6c2, 5373c9e |
| 1 (stopped) | 2026-10-19 | Error-analysis tooling (claim parser, labelling workbook, judge calibration, subject eval set, frozen retrieval set); hybrid recall 80/88/96% | 🤖 339 pytest | Preparing the 50-claim labelling made the plan's weight obvious: the user called it too complicated. Revisited the idea → **scope v3** | DECISIONS "Scope v3"; ERROR_LOG E-013 |
| M1 | 2026-10-19 | Research from passages: no fact extraction, graded passage relevance, 150-300-word sections, subject check in code, one model qwen3.5:4b | 🤖 351 pytest + 4 live runs | Two small-model surprises: thinking mode returned an empty plan (E-014) and a yes/no relevance question rejected nearly everything (E-015); a 0-3 grade fixed it. Same goal as E-001: honest gap report in 229 s instead of a confident wrong one | EVALS "v3 M1"; ERROR_LOG E-014, E-015 |
| M2 | 2026-10-19 | Run trace + feedback: desk database (one schema, two writers), every step, model call, retrieved chunk (ranks), grade, section input and sentence recorded; rating buttons per source and sentence on the report page | 🤖 358 pytest + 22 dashboard tests, live run through the backend (69 calls, 46 chunks, 44 sentences traced), headless Edge click test | The shared venv had broken the backend since Oct 10 (E-016): only a real end-to-end start finds that | DECISIONS "Run trace and feedback"; ERROR_LOG E-016 |
| Review + lock | 2026-10-19 | First real report reviewed against its chunks; citation repair, strict tables, copied summary, flag placement; report layout fixed; chunk size measured (Test A) and locked, library re-chunked uniform; harness for Tests B/C | 🤖 369 pytest + 22 dashboard tests; Test A over 6 sizes; headless-browser layout check | Fluent reports hide citation drift: true facts cited to the neighbouring chunk. Word overlap found it (0.08 vs 0.75). Locking the chunk size surfaced two chunker bugs (E-017) | EVALS "v3 Test A", "v3 report review"; DECISIONS; ERROR_LOG E-017, E-018 |
