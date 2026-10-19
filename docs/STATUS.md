# Status

**Scope:** v3 ([SCOPE.md](SCOPE.md)), agreed 2026-10-19 · **Next:** M1 Research from chunks (waits on your go) · branch `phase-1a0`
**Last updated:** 2026-10-19 · **Case study:** [CASE_STUDY.md](CASE_STUDY.md)

| Milestone | Status | Done when |
|---|---|---|
| M1 Research from chunks (one model, qwen3.5:4b) | not started | tests + live run; you read one real report |
| M2 Source panel + feedback | not started | baseline period of daily use starts |
| M3 Reranker | not started | measured offline, then before/after on your ratings |
| M4 Chat over the library | not started | a week of your own use |
| M5 Insights page + demo + README + case study | not started | 10-minute client demo |

Open errors: see [ERROR_LOG.md](ERROR_LOG.md). E-001 is addressed by design in M1 (no fact rewriting).

## For you (whenever convenient)

- Rotate the LangSmith key in `dashboard/.env.local` (printed once in an earlier session).
- Free RAM before model runs: close Unsloth Studio (:8888), extra Edge/Claude windows. qwen3.5:4b needs far less than v2's models.
- The 50-claim labelling (`claims.xlsx`) and `faithfulness_human.csv` are **no longer needed** (v3 drops them).

## Backlog

New ideas land here with the evidence that motivates them.
