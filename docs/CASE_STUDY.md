# Case study: a local research assistant that shows its work

> **Living document.** Updated at the end of every sprint (sprint log at the
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

## 3. Architecture

_Diagram added in Sprint 11._ In words: a LangGraph research graph
(goal → clarify → plan → coverage → collect wide → index all → rank → read
per question → verify → select ≤ 80 facts → write → checks → report) over a
local library (SQLite: sources, passages with FTS5 + vectors, fact bank).
Chat (Phase 2) is an agent over the same library.

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

Fix (planned, Sprints 6 and 8): structured facts with `system`, `size` and
`stage` fields; a subject check that compares fields in code; number
provenance and label rules enforced in code, not trusted to the model.

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

## 7. Measurements

_Filled from the scoreboard in `EVALS.md` at each gate._

| Metric | v6 baseline | Raw-passage baseline | v1.0 |
|---|---|---|---|
| Subject violations (30-fact sample) | — | — | — |
| Numbers traced to one fact | — | — | — |
| Label errors | — | — | — |
| Blind quality score (3 gold goals) | — | — | — |
| Minutes per report | — | — | — |
| Retrieval hit@k | — | — | — |

## 8. What I would do differently

_Collected as we go; finalised at v1.0._
- Start with error analysis and a simple baseline before adding pipeline stages (adopted late, in v2.2).
- Build the fast dev loop (saved evidence, mini fixture) before the first multi-hour run.

## 9. What's next

Phase 2 chat over the library, Phase 3 compounding knowledge, Phase 4 a
second domain and a client demo (private documents plus the web, on the
client's machine).

---

## Sprint log

One entry per sprint: what was built, what the tests showed, what surprised us, links.

| Sprint | Dates | Built | Tests (auto / manual) | Finding or surprise | Links |
|---|---|---|---|---|---|
| — | 2026-10-12 → 10-19 | Scope v2 → v2.2, process docs, build order | 328 offline + 19 dashboard pass | Free RAM stays ~5 GB even after a reboot; blocks the model test | DECISIONS scope entries |
| 0 | 2026-10-19 | Reviewed + committed the October fixes (plans stay on the goal, fetcher back-off), docs, dashboard snapshot; branch per phase | 🤖 328 pytest, ruff, 19 dashboard, tsc, eslint, secret scan · 🧑 U-01 pass | The review found prompt examples copied from the one test goal (E-010): a prompt fix tuned on the failing case can flatter the eval. Added a held-out goal to Sprint 1 | ERROR_LOG E-008..E-012; commits fb0d896, 4c9b6c2, 5373c9e |
