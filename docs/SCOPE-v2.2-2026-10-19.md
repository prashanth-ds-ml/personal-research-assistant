# Research Desk: scope v2.2 (LOCKED 2026-10-19)

v2.2 (2026-10-19) adds **Phase 1a-0 "Measure first"** (error analysis by
stage, eval set + scoreboard, fast dev loop, code audit), a **raw-passage
baseline** and a **critique on/off** comparison in the model test, the
**claim → quote check view** moved to Phase 1c as the product's centrepiece,
and **portfolio deliverables** in the Phase 1d gate. Phase 1b/1c tasks are
re-prioritised by the error analysis. Build order: `docs/BUILD_ORDER.md`.
v2.1 (2026-10-18) added: collect wide → index everything → read the best →
use a few (section 5); source states; an early chat preview at the end of
Phase 1b; the product direction (section 1). v2 was 2026-10-12.
Replaces `SCOPE-v1-2026-10-03.md` (kept for history). Locked by the user on
2026-10-18. Only items in the current phase are built; everything else goes
to the backlog (section 11). Changes after lock need a DECISIONS entry and a
version bump (v2.2, ...).

## 1. The product

**A local research assistant that builds you a knowledge base you own.**

- **Research:** give a goal; it plans with you, reads a bounded set of the
  best sources, and writes a report where every claim traces to a quote,
  names its real subject, is labelled by evidence strength, and says plainly
  what the evidence cannot answer.
- **Chat:** ask questions of your library in conversation; answers are cited,
  state what the library covers, and hand off to a full report when a
  question needs real synthesis.
- **Compounding knowledge:** every run adds checked sources and facts to a
  topic collection, so later chats and reports get faster and better, and
  work offline from what you have collected.

Runs fully locally (Ollama, no paid APIs, no cloud) on one laptop
(8 GB GPU, 24 GB RAM). Quality over speed: a report may take hours.

**First a good research assistant (Phase 1). Chat, compounding and domains
follow, but Phase 1 stores data so they need no rework.**

**Useful to the user first; then a private-first deep research product.**
The same system is later shown to clients as a demo or prototype: their
own documents plus the web, everything on their machine, every answer
traceable to a source. Client work (private sources, sign-in, per-user
access) is backlog until a real client asks; Phase 1 only records each
source's origin so it can be added without rework.

## 2. In and out

| In | Out |
|---|---|
| Two report types: **decision brief** and **state of the evidence** | Open-ended "write anything" reports |
| AI/ML research as the first domain (pack), generic core | Claims of "any domain" before a second pack is proven |
| Topic collections in one library | Multi-user, accounts, cloud hosting, paid APIs |
| Chat with the library (cited, coverage-aware) | A chatbot that answers from general model knowledge |
| Collect wide and index everything; bounded reading per run | Reading every collected document in one run |
| Works offline from the library; collection when online | "Never needs the internet": freshness is shown, not assumed |
| Desktop dashboard (existing Research Desk) | Mobile app; autonomous browsing agent |

## 3. Decisions this scope rests on

| ID | Decision | Why |
|---|---|---|
| S1 | **Research model: `gemma4:26b-a4b` (qat, ~16 GB)**, MoE ~4B active, GPU + RAM; one model reasons and writes. Confirmed by the model test (section 9) | Best quality that fits; same family as the best current writer |
| S2 | **Chat model: a fast model** (candidates `qwen3.5:9b`, `gemma4:12b` qat, `gemma4:e4b`), chosen by a small test in Phase 2 | Chat must answer in seconds; both models cannot stay loaded together, so they take turns |
| S3 | **Context 32k** for every research call (one setting, so the model loads once) | Holds the selected evidence with room; more context ≠ more reasoning |
| S4 | **The selected evidence must fit in one context** (section 5) | The decision step reasons over real facts, not summaries of summaries |
| S5 | **Structured facts**: generic core + domain-pack fields (section 6) | Makes "wrong subject" claims detectable by field comparison |
| S6 | **Fact bank**: every verified fact is stored and reusable | The knowledge base compounds; chat and later reports reuse checked facts |
| S7 | **Draft → critique → revise** for report chapters and decision | Quality is worth the time |
| S8 | **Rules in code, not trusted to the model**: number provenance, labels, gap statements | A bigger model errs less, not never |
| S9 | Reports are **1,500-3,000 words** (default, adjustable) | Small and mid models write a good section, not a good book |
| S10 | **Measure before building**: error analysis by pipeline stage decides which fixes come first; every phase updates one scoreboard against the v6 and raw-passage baselines | Effort goes where errors actually are; claims in the README point to numbers |
| S11 | **Simplest thing first**: a raw-passage writer (retrieve → best passages in 32k → write with quotes) is a baseline every pipeline change must beat | If structure does not beat it, structure is cut |
| S12 | **Fast dev loop**: a mini fixture (1 question, 5 saved sources, < 10 min) and writing replay from saved evidence; 3-5 h runs only at gates | Iteration speed decides quality more than model size |
| S13 | **Checking is the product**: one click from any claim to its highlighted source quote | A human verifies fast; that is what makes local AI research trustworthy |

## 4. Architecture

```
                         ┌───────────────── LIBRARY (one per user) ─────────────────┐
  Collect (online) ───►  │ Collections (per research topic)                          │
  Add URL / PDF    ───►  │   Sources (tier, version-merged, deduped, dated)          │
                         │   Passages (hybrid index: FTS5 + vectors)                  │
                         │   FACT BANK (verified, structured, cited, reusable)        │
                         └──────────────▲──────────────────────────────▲─────────────┘
                                        │                              │
   RESEARCH (big model)                 │        CHAT (fast model)     │
   goal → clarify → plan → coverage ────┘        question → retrieve passages + facts
   → approve plan + rules → collect wide         → cited answer + coverage statement
   → index ALL → rank → read best per question
   → verify → select ≤80 facts → write           → "make this a report" ──► RESEARCH
   → critique → revise → checks → report         (collect off by default)
   → new facts saved to the fact bank
```

## 5. Collect wide, index everything, read the best, use a few

A run handles sources at four levels, each cheaper and wider than the next:

| Level | What happens | Cost | Bound |
|---|---|---|---|
| **Found** | Search results for the plan's questions | Seconds | Collection rules (source types, sites, dates) |
| **Collected + indexed** | Fetched, converted, split into passages, embedded into the topic collection | No LLM; minutes (PDF conversion is the slow part) | L2 safety cap only |
| **Read** | The research model extracts and checks structured facts → fact bank | Hours | L3, L4 |
| **Used** | Facts in the report | One 32k context | L6, L7 |

Nothing collected is wasted: unread sources stay searchable by chat and are
the starting point of the next run on the topic. The user approves the
**plan and the collection rules**, not each source; a candidate list stays
available to exclude sources but is optional. Ranking for reading uses
relevance to the question, source tier and novelty.

**Source states** (stored per source, per collection): `indexed` (passages
only, unchecked) → `read` (facts in the fact bank) → `used` (in a report).
Chat and reports say which state their evidence comes from.
**Source origin** (stored per source): `web`, `upload`, later `connector`.

### Run limits (assumptions, checked in the model test)

The model never reads whole PDFs and never reads all documents at once.
Reading is limited by **time** (separate small calls); writing is limited by
**context** (one call holding all selected evidence).

| # | Limit / assumption | Value |
|---|---|---|
| L1 | Questions per report | 3-4 |
| L2 | Sources collected + indexed per run | no ticking; safety cap ~300 (time and disk) |
| L3 | Sources read per question | ≤ 12 |
| L4 | Sources read per run | ≤ 50 |
| L5 | Read from a source, per question | best 3-4 passages (~3k tokens) |
| L6 | Facts per source in the final evidence | ≤ 4 |
| L7 | **Facts in the writing step** | **≤ 80** (~20k tokens at ~200 per fact) |
| L8 | Sources that shape a report | ~20-25 |
| L9 | Library size | no hard limit |
| L10 | Time per report | ~3-5 h (estimate; measured in the test) |

All limits live in configuration, are shown in Settings, and anything left
out is listed in the run log and the report ("collected 286, read 47,
used 23; 239 indexed for later").

## 6. Fact format

**Core (every domain):**
`subject` (what the source is actually about, in its own terms) · `claim` ·
`quantity` + `unit` (optional) · `conditions` (setting, dataset, date) ·
`quote` (verbatim) · `source_id` · `passage_id` · `collection` · `checked`
(quote, support, subject) · `created_run`.

**AI/ML pack fields:** `system` (model/method name) · `size` (params) ·
`stage` (pretraining / continued pretraining / fine-tuning / post-training /
inference) · `task` · `dataset` · `metric` · `hardware`.

Subject check: a claim may only use size/stage/system terms present in its
passage's fields. "Pretraining a 4B model" from a 17B fine-tuning card fails
on `size` and `stage`, by comparison, not by judgement.

## 7. Capabilities and phases

Status: **built**, **fix** (exists, must change), **build** (new).
Each phase ends with its acceptance tests (section 8) before the next starts.

### Phase 1a-0: Measure first (no big model needed)

| ID | Capability | Status |
|---|---|---|
| P0.1 | Error analysis: ~50 claims from saved runs labelled by failing stage (retrieval miss / bad source / extraction subject / writing stitch / label) → `EVALS.md` | build |
| P0.2 | Eval set: subject-accuracy facts (extraction), existing `retrieval_qa.json` (retrieval), faithfulness sheet with the 8 disputed labels settled (writing); LLM judge calibrated on the user's labels | build |
| P0.3 | Scoreboard in `EVALS.md`: one table, rows = metrics, columns = v6 baseline, raw-passage baseline, each phase | build |
| P0.4 | Dev loop: mini fixture + fact viewer (passage / fact / verdict) | build |
| P0.5 | Code audit: v1 quick-research mode (`graph.py`, `lmstudio`, `notifications`, `utils`, `prompts`, `state`, Profile, `/new`, `/profile`, `/compare`) kept or archived by the user's decision | build |

### Phase 1: Research assistant v1.0 (quality)

| ID | Capability | Status |
|---|---|---|
| P1.1 | Model switch to the model-test winner (candidate `gemma4:26b-a4b`) at 32k; one model loaded for research | build |
| P1.2 | Run limits L1-L8 enforced in code; collected / read / used counts and "not read" / "not used" lists in log and report | build |
| P1.3 | Report types: decision brief, state of the evidence (plan templates) | fix (decision chapter exists in v1 plans) |
| P1.4 | Options become questions and a decision (one question per named option) | fix |
| P1.5 | Topic collections (on top of existing namespaces); run tied to a collection | build |
| P1.6 | Source tiers (paper > docs/primary > model card > blog > aggregator) | build |
| P1.7 | Version merge and dedupe (arXiv v1/v2, abs/pdf, repeated pages) | build |
| P1.8 | Structured fact extraction (core + AI/ML fields) | build |
| P1.9 | Subject check by field comparison; fail → rewrite to source terms or drop | build |
| P1.10 | Fact bank: verified facts stored with all fields; per collection | build |
| P1.11 | Selection: best facts per question within L6/L7 (relevance, tier, novelty) | build |
| P1.12 | Decision step over all selected facts (options, criteria, for/against, choice or "cannot decide") with thinking on | build |
| P1.13 | Draft → critique → revise for chapters and decision (1-2 rounds) | build |
| P1.14 | Summary written from the decision, not copied | fix |
| P1.15 | Number provenance: each number traces to one fact; stitched sentences relabelled | build |
| P1.16 | Labels: established (≥2 agreeing documents) / single source / synthesis / inference | fix |
| P1.17 | Evidence gate, gap notes, gap report, one-recommendation check | built |
| P1.18 | Coverage check, plan approval, collect choice, Stop, run records | built |
| P1.19 | Bugs from v1: garbled characters, run record single writer, per-run state, dead-Ollama check, plan check on resume | fix |
| P1.20 | Memory preflight (doctor): free RAM, GPU power, model fits without paging | fix (doctor exists) |
| P1.21 | Dashboard: commit and deploy the Research Desk redesign; collections in Library; limits in Settings | fix |
| P1.22 | Collect wide: discovery without the 40-candidate cap; plan + collection-rule approval replaces ticking; optional exclude list; every collected source indexed into the run's collection | fix (collect + auto-index exist) |
| P1.23 | Ranking for reading: relevance + tier + novelty, per question, within L3/L4 | build |
| P1.24 | Source states (`indexed` / `read` / `used`) and origin (`web` / `upload`) stored and shown in Library | build |
| P1.26 | **Claim check view** (Phase 1c): click any claim → its fact → the source passage with the quote highlighted; numbers and labels shown | build |
| P1.27 | Raw-passage baseline writer kept as a selectable mode for evals | build |
| P1.25 | **Chat preview** (end of 1b): one simple chat over a collection: hybrid search of passages + fact bank, cited answers, says which evidence is checked vs unchecked, refuses when the library has nothing; installed model; no agent loop, no threads | build |

### Phase 2: Chat with the library

| ID | Capability | Status |
|---|---|---|
| P2.0 | Built on the Phase 1b chat preview and what daily use of it showed | — |
| P2.1 | Chat model chosen by a small test (S2); model swap handled (unload research model) | build |
| P2.2 | Chat agent with tools: search passages, search fact bank, open source, coverage of a collection | build |
| P2.3 | Cited answers: every claim cites a passage or fact; numbers traced (same rules as reports) | build |
| P2.4 | Coverage statement in every answer ("based on N sources, newest from …; nothing on X") | build |
| P2.5 | Refuses to answer from general model knowledge; offers to collect or research | build |
| P2.6 | "Make this a report" → research run seeded from the chat (collect off by default) | build |
| P2.7 | Chat threads saved per collection; follow-up questions | build |
| P2.8 | Chat page in the dashboard (with evidence side panel, same reader style) | build |

### Phase 3: Compounding knowledge

| ID | Capability | Status |
|---|---|---|
| P3.1 | Reports from the library only (no collection), reusing fact-bank facts before re-reading | build |
| P3.2 | Fact reuse: skip re-extraction for sources already read for a similar question | build |
| P3.3 | Freshness: per-collection newest source date; "may be outdated" warnings in chat and reports | build |
| P3.4 | Contradiction view: facts on the same subject that disagree, side by side | build |
| P3.5 | Collection health: duplicates, junk, stale sources, coverage map | build |

### Phase 4: Second domain and studio demo

| ID | Capability | Status |
|---|---|---|
| P4.1 | Domain pack format (fact fields, source lists, tiers, report templates); AI/ML moved into it | build |
| P4.2 | Second domain pack (choose at phase start: e.g. healthcare evidence or business/markets) | build |
| P4.3 | Demo corpus per domain + one committed sample report and chat transcript each | build |
| P4.4 | Demo script: offline run, chat, report from library, evidence clicks | build |

### Packaging (alongside every phase; complete by end of Phase 1)

README with honest limits and diagram; `make setup / doctor / models / dev / test`
and Windows scripts; one Python version; demo corpus; CI (tests, lint, smoke);
demo video at the end of Phase 2 and Phase 4.

**Portfolio deliverables (part of the Phase 1d gate):** README hero (one
sentence, GIF of claim → quote, honest hardware); committed sample report
with its run record; evals page = the scoreboard; case study ("measured where
the agent failed, tried the simple fix first, the numbers"); architecture
diagram. **Pre-publish clean-up:** rotated keys and no secret in git history,
no personal vault/profile/archived reports in the repo, open-access demo
corpus, working notes in `docs/history/`. v1.0 is the public release;
Phases 2-4 ship as visible updates.

## 8. Acceptance tests (definition of done)

**Phase 1a-0**
- ~50 claims labelled by stage; error breakdown in `EVALS.md`; scoreboard has v6 and raw-passage baseline columns.
- Mini fixture runs end to end in < 10 min; writing replays from saved evidence.
- Code-audit decision recorded.

**Phase 1**
- Every structured stage added in 1b/1c beats the raw-passage baseline on the scoreboard, or is cut.
- Critique → revise kept only if it raises the blind score.
- The claim check view opens the highlighted quote for any claim in one click.
- Portfolio deliverables and pre-publish clean-up done.
- The known bad cases (E7/E8 post-training → "pretraining from scratch", E79 17B card → "4B pretraining", E76/E40 fine-tuned card) are caught by tests.
- 0 subject violations in a 30-fact random sample (manual check).
- 100% of numbers in summary and decision trace to a single fact.
- No "established" label on a stitched or single-source claim.
- Summary/decision overlap < 50%.
- Every run log shows collected / read / used counts; every collected source is in the collection's index; no prompt over its budget.
- Chat preview answers 10 questions over a collection with citations, marks unchecked evidence, and refuses 2 out-of-library questions.
- 3 gold goals (T1-T3) produce reports judged better than the v6 baseline on the blind checklist (subjects, numbers, decision, repetition, readability).
- Fresh clone runs via README; CI green.

**Phase 2**
- 30-question chat set over a demo collection: ≥ 90% answers fully cited; 0 uncited numbers; out-of-library questions refused with an offer to collect/research.
- Answers in < 20 s after the chat model is loaded.
- "Make this a report" produces a run whose plan matches the chat topic.

**Phase 3**
- A second report on a related goal reuses ≥ 30% of facts from the bank and is faster; quality not lower.
- Freshness and contradiction views correct on a seeded test collection.

**Phase 4**
- Second domain: 1 report + 10 chat questions pass the Phase 1/2 checks.
- Demo script runs offline end to end.

## 9. Model test (first task of Phase 1)

Same saved evidence (the SLM goal with known bad cases), 32k context:

| Run | Model | Role |
|---|---|---|
| 1 | `gemma4:26b-a4b` (qat) | candidate (S1) |
| 2 | `qwen3:30b-a3b` thinking (decision) + instruct (writing) | challenger |
| 3 | `gemma4:12b` (qat) | middle ground |
| 4 | `qwen3.5:9b` | fast baseline |
| 5 | `qwen3.5:27b`, decision step only | quality ceiling |
| 6 | current mix (llama3.1:8b + gemma4:e4b) | v6 baseline |
| 7 | winner of 1-5, **raw passages** instead of facts | simplest-thing baseline (S11) |
| 8 | winner of 1-5, with vs without one critique round | does reflection pay (S7) |

Measured: fits without paging, minutes per step, blind checklist score.
Precondition: reboot (free RAM), GPU power cap fixed, nothing else heavy
running. Result → `EVALS.md`; S1 confirmed or changed (new decision entry).

## 10. How we build

Per phase: tests first → build → full test run → review → every failure
logged with cause, fix and regression test → gate. Details in
`docs/PROCESS.md`; status in `docs/STATUS.md`; errors in `docs/ERROR_LOG.md`;
review questions in `docs/REVIEW_CHECKLIST.md`.

Phase 1 runs as five sub-phases, each with its own gate:
1a-0 measure first · 1a foundations + model test · 1b collecting + reading +
chat preview · 1c writing + claim check view · 1d hardening + v1.0
(`docs/phases/`). Sprint-level build order with test gates:
`docs/BUILD_ORDER.md`. Decisions in `DECISIONS.md`, evaluations in `EVALS.md`.
Which LangChain/LangGraph features to use for each item: `docs/FRAMEWORK_FIT.md`.

## 11. Backlog (not scheduled)

Reading figures/tables from PDFs with a vision model (gemma4 and qwen3.5
accept images) · reflection follow-up search for thin questions · Settings
for model roles · source-level goal triage at discovery · phone layout ·
export to Word/PDF · scheduled "what's new in my collection" digest ·
sharing a collection between two users · bulk folder import (client
documents) · **private sources for clients** (intranets and portals via
official connectors, IT exports or a signed-in crawler with written
permission; needs on-premise install, per-user access filtering on
passages, audit trail; for Indian banks RBI IT/outsourcing rules).

## 12. Decisions at lock (2026-10-18)

| ID | Question | Decided |
|---|---|---|
| Q1 | Run limits L1-L10 | As in section 5; tuned after the model test (a tuning, not a scope change) |
| Q2 | Topic collections in one library vs a separate library per topic | One library, collections per topic |
| Q3 | Second domain for the demo | Deferred by design: chosen at Phase 4 start, from Q7 |
| Q4 | Report length | 1,500-3,000 words |
| Q5 | Chat model | Preview: gemma4:e4b (installed); final by the Phase 2 test |
| Q6 | L2 collection safety cap | ~300 sources per run, adjustable in Settings |
| Q7 | First client type | Deferred by design: decided before Phase 4 |
