# Status

**Scope:** v3 ([SCOPE.md](SCOPE.md)), agreed 2026-10-19 · **Now:** M1-M3 done and released as **v0.3.1** (2026-10-22);
next is feedback from daily use, then M4 chat · branch `main` · **Last updated:** 2026-10-22
**Run it:** [SETUP.md](SETUP.md) · **Use it:** [USER_GUIDE.md](USER_GUIDE.md) · dashboard <http://127.0.0.1:3001>, backend <http://127.0.0.1:2025>
**Case study:** [CASE_STUDY.md](CASE_STUDY.md)

| Milestone | Status | Done when |
|---|---|---|
| M1 Research from chunks (one model, qwen3.5:4b) | **done**: passages, citation repair, strict tables, extractive summary, figure/subject/wording/domain flags | - |
| M2 Source panel + feedback | **done**: run trace + desk database + rating buttons; layout fixed | daily use starts |
| Chunk size | **locked: `v2 text=1800 table=3000`** (Test A); library uniform; new sources follow automatically | done |
| Tests B, C, D | **done**: best 8 passages per section, best first, 400-600 words; no neighbour expansion; thinking when writing ON | done |
| M3 Reranker + source quality | **done 2026-10-20**: reranker on (offline top-3 88% -> 100%, mixed on real runs); planner fix (E-019); papers and docs ranked first; arXiv query fixed; domain flag | before/after on your ratings |
| M4 Chat over the library | not started | a week of your own use |
| M5 Insights page + demo + README + case study | not started | 10-minute client demo |

**Final report (run 01a158a7, 17 min):** *Local Private RAG System Design for Small Teams* - 5 of 6 sections (embedding-model
memory is an honest gap: no source in the library), 2,979 words, 5 papers / 3 docs / 10 web pages, 93% of 155 sentences clean.
Details in [EVALS.md](../EVALS.md) ("v3 final report after all fixes"); limits in the case study (section 7b).

## Next, in order
1. Your feedback: read the final report in the dashboard, rate sources (👍/👎/⚠) and flag wrong sentences; run your own goals.
2. M4 chat over the library (same retrieval engine + reranker).
3. M5 insights page and demo (README, setup and user guides were done for the v0.3 release).

## For you
- Rate the sources and flag sentences on the final RAG report and any new ones.
- Before a run: free RAM >= 11-12 GB (Ollama maps ~8 GB on Windows, E-022); close heavy apps.
- A backup of the library before the re-chunk is at `<vault>/.kb/library.before-chunker-lock-2026-10-19.sqlite`
  (keep it or remove it yourself; nothing is deleted automatically).

## Starting the app
- Backend: `uv run langgraph dev --no-browser --no-reload --port 2025` (in this folder; see [SETUP.md](SETUP.md))
- Dashboard: `cd dashboard && npm run start` (production build; after code changes run `npm run build` first, never while a run is live)
- Open errors: [ERROR_LOG.md](ERROR_LOG.md)

## Backlog
- A doctor check for a run's real memory need; bge-reranker-base when RAM is short (E-022).
- A per-document chunk cap (one dataset card produced 759 chunks).
- Fail loudly when the planner returns nothing (E-014 pattern).
- `scripts/doctor.py` could import `langgraph_api.server` to catch a broken shared venv (E-016).
