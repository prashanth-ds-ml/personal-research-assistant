# Dashboard redesign: "The Research Desk"

Status: phases 1 to 7 built on 2026-10-02 (not yet deployed to the live servers, not committed). Phase 8 verification done except a human click-through. Design source: the approved mock (Claude design canvas, Version 13).
Everything stays local. No new network calls, no external fonts, no new paid services.

## Principles

1. One design system (tokens in `globals.css`), so every existing page picks up the new look without a rewrite.
2. Real data only. Where the mock showed sample numbers, the page reads the vault, the run records or the local machine.
   Where no real data exists yet, the page says so honestly instead of showing fake numbers.
3. Do not break the running dashboard. Two `next start` servers (ports 3000 and 3001) use the built `.next` folder, so
   development uses a separate dist folder (`NEXT_DIST_DIR`) and a different port. No `npm run build` while they run.
4. Small, reviewable commits, one per phase.

## Phases

| # | Phase | What ships | Real data source |
|---|---|---|---|
| 1 | Foundation | Paper/ink palette, serif headings (system stack, no web fonts), sharper corners, light/night/system theme toggle, masthead navigation replacing the sidebar, Ctrl K command palette, memory chip | `/api/system`: Ollama `/api/ps` and `/api/tags`, `os.freemem()` |
| 2 | Reports | Newsstand at `/reports` with generated cover art, search, filters, empty states | vault notes |
| 3 | Magazine reader | `/research/[slug]` as a magazine: cover, contents, drop cap, columns, margin quotes for `[E#]`, pull quote, label tags, evidence figure, sources, reading controls, progress, faithfulness panel, highlight menu | report markdown (sections, evidence table, appendix) |
| 4 | Front page | `/` with brief box, readiness card, continue strip, latest issue, ideas from your library, recent issues, first-run state | runs, notes, `/api/system` |
| 5 | Compare | `/compare` for two issues of the same goal: evidence per chapter, recommendation, sources added | two notes |
| 6 | Library | `/library`: documents indexed from the vault's source folders, filter by kind, search | vault files |
| 7 | Re-skin | Runs, run detail, Deep research (chapter bar), Quick research, Knowledge graph, Pipeline graph, Profile: new tokens, serif headings, empty states | existing |
| 8 | Verify | typecheck, lint, tests for the report parser, dev-server smoke check of every route | |

## Deferred, with reasons

- Settings page: it would write `.env` and restart services; needs its own safe design (what is writable, what restarts).
- Per-document "facts used" and chunk counts in the Library: the index is in SQLite owned by the Python side; a read-only
  endpoint there is the right way, not the dashboard opening that database.
- Generated covers from each report's real knowledge-graph neighbourhood: v1 uses a deterministic pattern from the
  report's own section facts.
- Real web fonts (Newsreader, Instrument Sans): add `@fontsource` packages later if wanted; the system stack
  (Iowan Old Style, Palatino, Georgia) already reads as editorial.

## Risks

- Next.js 16 differs from older versions: read `node_modules/next/dist/docs/` before using a new API.
- Report parser must never throw on a hand-edited note: fall back to plain markdown rendering.
- Selection-based highlight menu must not send selected text anywhere; it only builds a link into `/deep?goal=`.

## What was built (2026-10-02)

Phases 1 to 7 are in `dashboard/`. New: `src/lib/{report,compare,library,system}.ts`, `src/components/{masthead,command-palette,
memory-chip,theme-toggle,cover-art,magazine-reader,brief-box,free-memory-button}.tsx`, pages `/reports`, `/library`,
`/compare`, a new `/` front page, API `/api/system`, `/api/system/free`, `/api/reports`. The old sidebar and mobile nav are
removed. Existing pages (runs, run detail, deep, quick, profile, knowledge, pipeline graph) took the new tokens, serif
headings and square corners.

Differences from the mock, on purpose:
- Highlight menu has Copy as citation and Research this deeper. "Explain simply" and "Show the quote" are not built:
  the first needs a model call, the second is already the margin note beside each citation.
- The time estimate is a fixed "30 to 60 minutes": run records include time spent waiting for the user, so a measured
  average would mislead.
- Library is read only (no remove, no re-index): those belong to the Python side.
- Night theme is a real token palette (not an inverted filter); "Paper / Night" remembers the choice, otherwise the system setting wins.
- "Unload models" really calls Ollama (`keep_alive: 0`), so the memory number on the front page can improve at once.

## Verification

- `npx tsc --noEmit` clean, `npx eslint src` clean, `npm test` (11 tests for the report parser and the comparison).
- A separate dev server (`NEXT_DIST_DIR=.next-dev`, port 3100) returned 200 for every route and both API routes; the
  live servers on 3000 and 3001 were never touched. Headless screenshots checked the reader, front page, reports,
  library, compare, runs, run detail and the graph in light and dark.
- Not done: a human click-through of Ctrl K, the highlight menu, theme toggle and the memory button in a real browser session.

## Putting it live

The two running servers use the old build. When no run is in progress:
1. stop both `next start` processes (ports 3000 and 3001),
2. `cd dashboard && npm run build`,
3. start them again (`npm start` for 3001).

## Round 2 (2026-10-02, after the first review): every mock screen, real backends

The first pass followed the mock's look but not its screens. Round 2 rebuilt each screen to the mock's layout and wired
the buttons to real behaviour:

| Screen | What it does now |
|---|---|
| Layout | Full width (1680 px cap, 56 px side padding), as in the mock boards |
| Library | Reads the real index (`.kb/library.sqlite`, read only): 110 docs, chunks, facts used, preview from the stored text. Add sources (collector, job with progress), Re-index one document, Remove (takes it out of the index and moves the file to `<vault>/.removed`, never deletes) |
| Runs | Master/detail: list with filter tabs on the left, run header, Stop with confirmation, stage pills, three counts, Newswire, collected sources on the right |
| Research (`/deep`) | Six-step chapter bar. Brief (desk cards, readiness, archived-pages option, starters), Questions one at a time, Plan with coverage rows that open to their documents, Sources in two columns with preview and tick all, Progress with the press strip and live counts, Report |
| Graph | Obsidian style: search, per-type filters, labels, node size, link distance, local graph, zoom and pan, hover tip, details with Remove. Links come from each report's own Sources list |
| Pipeline | Deep and Quick tabs, step chips, legend, details panel (reads, writes, model, time) |
| Quick research | Mock layout: loops stepper, search select, step chips, result card |
| Profile | Edit the whole note (previous version kept as `Profile.md.bak-<date>`), standing preferences, topics, feedback lessons with Forget, recent additions, Reset |
| Settings | New. Models (from what Ollama has installed), Sources (toggles, no limit, per-site chips), Report quality, Library and vault (re-index, rebuild), Privacy. Writes a fixed whitelist of lines in `.env`; everything else in the file is untouched and never read into the page |

Python side: `KnowledgeBase.remove()` (tested), `scripts/library_doc.py` (reindex/remove one document, path-checked).
Dashboard side: `lib/{library,pyrun,jobs,graph,profile,settings}.ts`; the scripts run without a shell and without the dashboard's
own environment (its `EMBEDDING_MODEL` is spelled differently and broke re-indexing until this was found by testing).

Bugs found by running it: a server-only import in a client component (500 on /library), a graph layout that rendered
different float digits on server and browser (hydration warning), and the environment leak above.

Clean start: reports and run records were moved (not deleted) to `C:\Users\me\ObsidianVaults\Research-archive-2026-10-02`.
Sources, Library, the index and Profile.md were kept.

Known and honest: "Settings" saves to `.env`, which the Python backend reads when it starts, so a restart is needed to
apply changes. `.next` of the live servers still holds the old build until they are rebuilt.

## Round 3 (2026-10-02): design review fixes

From a design review of the running app. Done:
- Masthead run chip on every page ("Run · stage 5 of 7, evidence" / "Waiting for you · approve the plan"), links to the run.
- The front page leads with a run that needs you and shrinks its greeting and brief box while a run is active.
- "What to do next" links in every empty state (Profile, Home recent issues; Library, Runs, Reports, Compare, Graph already had them).
- Failures use an error card that says what is wrong and how to fix it ("the research engine is probably not running: langgraph dev") with Try again and Show details. `/api/system` now reports whether the research engine answers, and the Brief screen lists it.
- Toasts (bottom of the screen, fade by themselves, errors stay longer) for save, remove, re-index, forget, reset and unload.
- Unsaved-changes guard on Settings, Profile edit and the Library add box (browser close and in-app links).
- Reader below 1024 px: the evidence and quotes fold open under their chapter instead of sitting in a margin that is not there.
- Earlier in the review: phone-width Library table, headline sizes, readable placeholder, masthead alignment, skip link, modal semantics, memory chip wording.

Verified with a real run paused at its questions and at plan approval: the chip, the busy front page, the Runs detail, the Questions screen and the Plan screen all rendered correctly from live data. Not verified by eye: toasts, the unsaved guard and the error card (they need clicks or a stopped engine).

## Round 4: questions and answers on the Runs screen

The run detail showed counts but not the questions. It now shows "Questions it asked you" (each question with your answer, or
"left to the assistant") and the plan's questions with the library coverage, the facts found and where the run is.
New runs record these in the run record (`clarify_questions`, `clarifications`, `plan`, `question_facts`; `goal_graph.py`,
tested by `test_qa_pairs_turns_the_dashboard_answer_text_back_into_pairs`). For any run that lacks them, including a run in
progress, the dashboard reads the same data from the research engine's saved state, so nothing needs restarting to see them.
The engine itself must be restarted once for NEW runs to write the new fields.
