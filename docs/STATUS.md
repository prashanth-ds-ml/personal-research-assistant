# Status

**Scope:** v3 ([SCOPE.md](SCOPE.md)), agreed 2026-10-19 · **Now:** M1 + M2 built and tested; your real-goal run is next · branch `v3`
**Test here:** dashboard <http://localhost:3001> · backend <http://127.0.0.1:2025>
**Last updated:** 2026-10-19 · **Case study:** [CASE_STUDY.md](CASE_STUDY.md)

| Milestone | Status | Done when |
|---|---|---|
| M1 Research from chunks (one model, qwen3.5:4b) | testing: 351 tests pass; live run 229 s, honest gap report (EVALS v3 M1) | you run one real goal in the dashboard and read the report |
| M2 Source panel + feedback | built (pulled forward on 2026-10-19): run trace + desk database + rating buttons; 358 + 22 tests, live run and headless-browser check | baseline period of daily use starts |
| M3 Reranker | not started | measured offline, then before/after on your ratings |
| M4 Chat over the library | not started | a week of your own use |
| M5 Insights page + demo + README + case study | not started | 10-minute client demo |

Open errors: see [ERROR_LOG.md](ERROR_LOG.md). E-001 is addressed by design in M1 (no fact rewriting).

## For you (whenever convenient)

- Rotate the LangSmith key in `dashboard/.env.local` (printed once in an earlier session).
- Free RAM before model runs: close Unsloth Studio (:8888), extra Edge/Claude windows. qwen3.5:4b needs far less than v2's models.
- **M1 test:** run one real research goal from the dashboard (with collecting on) and read the report.
- The 50-claim labelling (`claims.xlsx`) and `faithfulness_human.csv` are **no longer needed** (v3 drops them).

## Backlog

New ideas land here with the evidence that motivates them.
