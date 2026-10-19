# Next steps for project 4 (end of session 2026-10-01)

> **Superseded for planning by [`SCOPE.md`](SCOPE.md) v2 (2026-10-12) and [`STATUS.md`](STATUS.md).** Kept as history; open items here are tracked in `ERROR_LOG.md` (E-003..E-007) and the phase docs.

State: deep research with coverage check, source collecting with review, evidence gate, claim labels, run records, Stop and Runs
page is built and committed (285 offline tests, lint clean, 25 commits). Services run the latest code (dashboard 3001, backend 2025,
both on 127.0.0.1). Full list of findings: `closeout-review-2026-10-01.md`. Measurements and the finish plan: `model-memory-plan.md`.

## Machine (updated at the start of the next session)
The GPU power cap is **gone**: power limit 112-115 W (was 10 W), llama3.1:8b generates at 64 tokens/s (healthy runs on 30 Sep: 53). Cause
not identified (charger or OMEN mode, fixed by you). `python scripts/doctor.py` now checks this (power limit against default), plus Ollama,
models, vault, `.env`, free memory and ports. Still open: free RAM is 3-4 GB (the gemma writer maps about 5.4 GB), a 15 GB python job from
28 Sep (PID 45288, not ours; your call), an unidentified 4 GB `vmmem`.

## Still to do, in this order
1. **README and setup (blocks a stranger).** Done: `scripts/doctor.py` (+ `src/research_assistant/doctor.py`, 7 tests). Left: rewrite the top (deep-research quick start, diagram of both graphs, prerequisites, model sizes,
   honest limits); Makefile or setup scripts; demo corpus (6-8 open-access papers) and one committed sample report;
   regenerate `uv.lock` as its own step; one Python version (3.11/3.12); re-check `langgraph dev` in a fresh clone; move working notes to
   `docs/history/`; CONTRIBUTING, CHANGELOG; fix `dashboard/README.md`.
2. **Bugs left (medium):** run record still has two writers (use a separate stop file); global `STOP`/`LLM_STATS` shared across runs;
   a dead Ollama passes plan/coverage/discover silently; resume does not check the plan is unchanged; /deep Stop should also POST
   `/api/runs/{id}/stop`; LangSmith lookup blocks the report page; dashboard Docker image runs as root.
3. **Validation (the GPU is fast again, so this can run now; close big programs first for RAM):** the saved small-model goal (`logs/goal-slm.txt`) with collect-for-gaps; compare with the original
   report; record the exit tests of `report-quality-plan.md` in EVALS.md. The out-of-coverage test already passed (below).
4. **Memory/speed:** explicit model unload between phases, `OLLAMA_MAX_LOADED_MODELS=1`, low-memory warning on the run page, choose the
   writer by measured speed (gemma4:e4b needs about 5.4 GB of system RAM for its mapped weights).
5. **Finish:** CI (Python matrix, `langgraph dev` smoke, compose build), fresh-clone and Docker run, demo video (script in the close-out
   review), tag v1.0.

## Cut line (not planned)
Deliverable-aware planning (stage 6), disagreement detection, recursive crawling, `collect.py --web`, merging the two collectors,
auto-tuned thresholds.

## User-owned
- GPU power cap (above); the browser click-through of `/deep` (coverage card, collect choice, review lists, Stop), `/runs`, `/`.
- Rotate the LangSmith key in `dashboard/.env.local` (printed once in the session transcript).
- Check the 8 contestable faithfulness labels (ids 2, 9, 11, 16, 25, 31, 34, 39 in `evals/faithfulness_sheet.csv`).
