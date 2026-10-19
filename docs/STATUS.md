# Status

**Scope:** v3 ([SCOPE.md](SCOPE.md)), agreed 2026-10-19 · **Now:** M1 + M2 built; report checks tightened; chunk size locked;
Tests B and C next · branch `v3` · **Last updated:** 2026-10-19 (end of session)
**Test here:** dashboard <http://localhost:3001> · backend <http://127.0.0.1:2025> (start commands below)
**Case study:** [CASE_STUDY.md](CASE_STUDY.md)

| Milestone | Status | Done when |
|---|---|---|
| M1 Research from chunks (one model, qwen3.5:4b) | built; first real report reviewed 2026-10-19; fixes in (citation repair, strict tables, extractive summary, flags before the stop) | your feedback on real reports |
| M2 Source panel + feedback | built: run trace + desk database + rating buttons; layout fixed (margin no longer stretches chapters) | daily use starts |
| Chunk size | **locked: `v2 text=1800 table=3000`** (Test A); library re-chunked and uniform; new sources follow automatically | done |
| Tests B and C (neighbour expansion; passages per section / context use) | harness ready (`scripts/exp_context.py`); not run yet | numbers in EVALS; section budget chosen |
| M3 Reranker | not started | measured offline, then before/after on your ratings |
| M4 Chat over the library | not started | a week of your own use |
| M5 Insights page + demo + README + case study | not started | 10-minute client demo |

## Next session, in order
1. Rebuild the Test B/C passage pool (the library was re-chunked after it was built, so its chunk ids are stale):
   `python scripts/exp_context.py pool` (~5 min), then `... c`, `... b`, `... think` (~45 min, automatic).
2. Pick passages per section and the context window from Test C; decide on neighbour expansion from Test B; record in
   EVALS and DECISIONS; set the budgets in `deep_report.py`.
3. Your feedback on the embeddings report (rate sources, flag sentences) and on new reports.
4. Small wording leftovers: the progress text still says "Extracting evidence"; the status table says "Facts" for passages.

## For you
- Rate the sources and flag sentences on *Embedding Models: Architecture, Training Data, and Pipeline Construction*.
- Rotate the LangSmith key in `dashboard/.env.local` (printed once in an earlier session).
- A backup of the library before the re-chunk is at `<vault>/.kb/library.before-chunker-lock-2026-10-19.sqlite`
  (keep it or remove it yourself; nothing is deleted automatically).

## Starting the app
- Backend: `langgraph dev --no-browser --no-reload --port 2025` (in this folder, with the root venv)
- Dashboard: `cd dashboard && npm run start` (production build; after code changes run `npm run build` first, never while a run is live)
- Open errors: [ERROR_LOG.md](ERROR_LOG.md)

## Backlog
- Fail loudly when the planner returns nothing (E-014 pattern).
- `scripts/doctor.py` could import `langgraph_api.server` to catch a broken shared venv (E-016).
