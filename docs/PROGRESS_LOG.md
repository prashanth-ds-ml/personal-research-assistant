# Progress log: how Research Desk was built

The detailed record behind the [case study](CASE_STUDY.md): every stage, measurement and decision, in order. Numbers link to [EVALS.md](EVALS.md); bugs to [ERROR_LOG.md](ERROR_LOG.md) (E-numbers); decisions to [DECISIONS.md](DECISIONS.md). Internal names used here: **v1 / v2 / v2.2 / v3** are scope versions; **M1-M5** are v3 milestones; **Tests A-D** measured chunk size, passages per section and section length.

## Timeline

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
| 2026-10-19 → 10-20 | M1-M3 | Reports from passages, run trace + feedback, chunk size locked, section budget measured (Tests A-D), reranker, source-quality fixes |
| 2026-10-22 | **Public release v0.3** | Repo cleaned for strangers: install path, README, setup and user guides, CI on every push; a hidden ignore rule had kept the whole Library page out of git |

## Scoreboard by engine version

Filled from `EVALS.md` at each gate.

| Metric | v2 (facts) | v3.0 hybrid | v3.1 rerank |
|---|---|---|---|
| Retrieval recall@1/3/6 (frozen set, 25 questions) | 80/88/96% | 80/88/96% | 88/100/100% (offline) |
| Useful passages in the writer's top 8 (real run, audit) | — | 28 of 48 | 32 of 48 |
| Sources rated relevant (your feedback) | — | — | collecting from daily use |
| Reports/answers rated helpful | — | — | collecting from daily use |
| Sentences passing every code check | — | 86% (run 1, full test) | 92-96% (thinking on); 93% final report |
| Words per report (body) | ~4,000 | 1,289-1,632 | 2,893-3,534 (400-600-word sections) |
| Minutes per report (library only) | hours | 3.8 | 6.2 (no thinking) / 16.5-17 (thinking) |
| Wrong-subject claims found on reading (same goal) | several | 0 | flagged in code (subject and domain checks) |

The reranker's offline gain is clear; on two real runs it was small and mixed (32 vs 28, then 25 vs 27 useful passages).
It stays on because it rescues passages hybrid buries (once from rank 18). Sources: EVALS "v3 M3 reranker",
"v3 full-pipeline test", "v3 end-to-end audit", "v3 final report after all fixes".

## Decisions and trade-offs (full table)

| Decision | Alternatives rejected | Why |
|---|---|---|
| The model's context bounds a report, not the number of documents | "Read every PDF" | The decision step only ever saw ~24 compressed sentences; compression is where subjects got lost |
| Collect wide, read the best, keep the rest searchable | Tick ~100 candidates by hand | Doesn't scale to hundreds; unread sources still feed chat and later runs |
| One mid-size MoE model (candidate `gemma4:26b-a4b`), confirmed by test (v2; replaced in v3 by one 4B model, below) | Max context; several small models | Fits 8 GB GPU + RAM; one model loaded at a time |
| Measure first: error analysis by stage, raw-passage baseline | Fix by diagnosis | Effort goes where errors are; complexity must beat the simple thing |
| Rules in code (provenance, labels, gaps) | Trust a bigger model | A bigger model errs less, not never |
| Write from reranked chunks (v3) | Extract facts, then write from facts | The paraphrase step was where subjects got lost (22/42 right); retrieval was already good (96% recall@6) |
| One 4B model for plan, write and chat (v3) | Planner/extractor + separate writer | With extraction gone only light jobs remain; no model swapping on a memory-short laptop |
| Feedback from daily use as the evaluation (v3) | 50-claim labelling sheet, judge calibration | Labels arrive as a side effect of using it; before/after numbers from real use |

## Lessons from failures (full table)

| Lesson | What happened | Source |
|---|---|---|
| A verifier needs its own positive and negative test | The faithfulness judge rejected everything because of contradictory prompt rules; a full run produced 0 evidence | DECISIONS "The faithfulness judge was broken by my own prompt" |
| Retrieval failures hide as writing failures | A section kept being wrong after prompt fixes; the retriever never found the right paper. Found by reading retrieved passages, not the report | DECISIONS "Retrieval failures hide as writing failures" |
| A streaming call never times out | One model call generated ~79k tokens for 1.5 h; the HTTP read timeout resets on every token | DECISIONS "A streaming model call can never time out" |
| Check the machine before blaming the model | Runs were 5-10× slow: the GPU was capped at 10 W, not a memory problem | DECISIONS "The slowdown was mostly a power-capped GPU" |
| Dependencies change under you | Search returned nothing, silently: the package had been renamed upstream | DECISIONS "The search backend was silently broken" |
| Measure model choices on your own prompts | The tutorial's suggested model was not the fastest; the original default was the slowest of seven | v1 benchmarks (archive/v1-2026-09-29-to-10-03.md) |

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
| Tests B/C | 2026-10-20 | Measured how much source text the 4B model uses per section: accurate up to ~5k tokens, but uses ~8 passages (section length) and drops late ones; neighbour expansion doubled input for no gain. Section budget set to the best 8, best first | 🤖 48 measured section writes + 370 pytest | The limit was not the context window (256k) but the section length and position bias; thinking removed the bias at 10x the time | EVALS "v3 Tests B and C"; DECISIONS "Section budget" |
| Test D | 2026-10-20 | Measured how long a section can be: accurate up to ~600 words; at 800-1000 a quarter of sentences carry no source. Basis for the stated limits: <= 8 passages and <= ~600 words per section, reports ~1,000-3,000 words | 🤖 48 measured section writes, ~11 min | The 4B model fails by padding with unsourced sentences, not by repeating or drifting | EVALS "v3 Test D" |
| Full test | 2026-10-20 | Reranker built (CPU cross-encoder, M3) and tested offline (top-3 88% -> 100%); one long report run three ways (hybrid / + reranker / + reranker + thinking when writing) | 🤖 3 full backend runs, offline reranker test, 375 pytest | The reranker lifts buried chunks, but on a small topic the report barely changes; thinking when writing gave the clearest gain (92% clean sentences, +7 min). The weak point of long reports is the plan, not the writing (E-019) | EVALS "v3 M3 reranker", "v3 full-pipeline test" |
| E2E audit | 2026-10-20 | Full pipeline from cleared RAM/GPU, audited from its trace: health, reranker head-to-head, writer use, claim support, sources, UI | 🤖 1 full run, scripts/audit_run.py, headless browser | 94% of 180 sentences clean; the reranker beat hybrid 32 vs 28 useful passages and rescued 28% of what the writer used; the weak point is now the sources (15 web pages, 1 paper) | EVALS "v3 end-to-end audit" |
| Source fixes | 2026-10-20 | Papers and AI-engineering docs ranked first, arXiv query fixed (0 -> 4-5 papers per question), domain-specific sources must be named, refined on-subject relevance | 🤖 2 verification runs + audits, 391 pytest | Fixing one weakness exposed the next: a stricter relevance rule cost 3 sections until re-graded; the final report has 5 of 6 sections from 5 papers, 3 docs, 10 web pages | EVALS "v3 final report after all fixes" |
| Release v0.3 | 2026-10-22 | Public release prep: secrets/personal-data audit of all history (clean; unpushed commits rewritten to drop paths and names), one default model everywhere, reranker deps as an extra, doctor checks reranker + real memory need, CI on every push, Docker removed (it set up v1), README + setup guide + user guide | 🤖 392 pytest, 22 dashboard tests, ruff, tsc, eslint, history secret scan | A `library/` ignore rule had silently kept the Library page and its 7 API routes out of git for weeks: it worked on this machine and would have 404'd on every clone. Only a stranger's-eye review finds that. Then a fresh-clone install failed (uv picked Python 3.14, where `tiktoken` has no wheel; fixed by pinning 3.12) and the first CI run failed (Next's `PageProps` types only exist after a build). Everything worked on the dev machine; each clean start found one more thing. A live run the same morning stalled 17 min on one PDF (no per-source time limit; listed as a known limit) | docs/archive/release-plan-2026-10-22.md, docs/SETUP.md, docs/USER_GUIDE.md |
| Quick start v0.3.2 | 2026-10-22 | Two-command setup for people who clone the repo: `scripts/setup.py` (checks tools, installs the tested versions, pulls models, writes settings, builds the dashboard, runs the setup check; safe to re-run) and `scripts/start.py` (both servers, one Ctrl+C); versions pinned to the daily-use environment | 🤖 403 pytest, 22 dashboard tests, CI; 10 release checks incl. a fresh-clone install, browser check of the new install, re-run, missing-tool messages and a clean stop | The fresh clone found what the dev machine hid: the dashboard never looked in the project's own `.venv` (it relied on the shared one two folders up), and the lock file had drifted from the environment the reports were made in (103 packages). "Works on my machine" was literally true | docs/SETUP.md, README quick start |
