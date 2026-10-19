# Research Desk: rules for working in this repo

Local research assistant: bounded, checked research reports plus (Phase 2)
chat with a growing library and fact bank. Ollama only, no paid APIs, no cloud
by default. Quality over speed.

## Read first
- `docs/STATUS.md`: current phase, blockers; `docs/BUILD_ORDER.md`: sprints and test gates
- `docs/SCOPE.md` (v2.2): what we build; `docs/FRAMEWORK_FIT.md`: which LangChain/LangGraph features to use
- `docs/PROCESS.md` and the current `docs/phases/*.md`
- `DECISIONS.md` (append-only), `EVALS.md`, `docs/ERROR_LOG.md`, `docs/USER_TESTS.md`, `docs/CASE_STUDY.md`

## Working rules
- Discuss before implementing; do not start a phase or a large change without the user's go-ahead.
- Build only the current phase; ideas go to the STATUS.md backlog. Say so when a request is outside the locked scope.
- Tests first, named by test-case ID. Every bug or finding → ERROR_LOG entry → fix → regression test.
- Record evaluation results in EVALS.md whatever they show; update the scoreboard at every gate.
- Measure first: a new pipeline stage must beat the raw-passage baseline on the scoreboard or it is cut. Develop on the mini fixture; full runs only at gates.
- Test everything possible yourself (live model, API, Playwright, secret scan, fresh clone); only what needs a person goes to `docs/USER_TESTS.md`.
- End of every sprint: STATUS, phase Results, ERROR_LOG, USER_TESTS, and a `CASE_STUDY.md` sprint-log entry. At a gate also the EVALS scoreboard.

## Non-negotiables
- Facts name their real subject (structured fields); numbers trace to one fact; labels follow the rules; gaps are stated.
- Research is an explicit LangGraph graph; agent loops only in chat.
- No silent truncation: budgets enforced and logged; collected / read / used reported.
- Library/vault content is never deleted (moves to `.removed`).

## Machine and tooling gotchas
- Python: shared root venv `../../.venv` (uv); install with `uv pip`. Do not regenerate `uv.lock` casually.
- 8 GB GPU + 24 GB RAM. Check free RAM and GPU power (`python scripts/doctor.py`) before model runs; one model loaded at a time.
- Do not `npm run build` the dashboard while a run is live (servers on 3000/3001 serve the old build).
- Long nested heredocs in the Bash tool fail; use Write/Edit. Use `C:\` paths for Windows Python + sqlite.
- Never print `.env` files unfiltered (a LangSmith key leaked that way once).
