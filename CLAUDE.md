# Research Desk: rules for working in this repo

Deep research that builds a private library (primary) plus chat over that
library (secondary), with user feedback improving both. One local model
(`qwen3.5:4b`), Ollama only, no paid APIs, no cloud.

## Read first
- `docs/STATUS.md`: current milestone; `docs/SCOPE.md` (v3, one page): what we build and the milestones M1-M5
- `DECISIONS.md` (append-only), `EVALS.md`, `docs/ERROR_LOG.md`, `docs/CASE_STUDY.md`
- Older plans (v2.2 sprints, phases, user tests) are in `docs/archive/v2.2/`: history, not instructions

## Working rules
- Discuss before implementing; do not start a phase or a large change without the user's go-ahead.
- Build only the current milestone; ideas go to the STATUS.md backlog. Say so when a request is outside the scope.
- Keep it simple: do not add process, documents or stages the scope does not need. The user's daily use and feedback are
  the evaluation; do not hand the user labelling or test chores.
- Tests first, named by test-case ID. Every bug or finding → ERROR_LOG entry → fix → regression test.
- Record evaluation results in EVALS.md whatever they show; update the scoreboard at every gate.
- A new stage or model change must show its effect (retrieval set, code-check pass rate, feedback per engine version) or it is cut.
- Test everything possible yourself (live model on a small goal, API, dashboard, secret scan).
- End of every milestone: STATUS, ERROR_LOG, EVALS, and a `CASE_STUDY.md` progress-log entry.

## Non-negotiables
- Every report/chat sentence cites a chunk; numbers and model names appear in the cited chunk (checked in code); gaps are stated.
- Feedback is stored with the engine version so before/after comparisons are possible.
- Research is an explicit LangGraph graph; agent loops only in chat.
- No silent truncation: context budgets enforced and logged.
- Library/vault content is never deleted (moves to `.removed`).

## Machine and tooling gotchas
- Python: shared root venv `../../.venv` (uv); install with `uv pip`. Do not regenerate `uv.lock` casually.
- 8 GB GPU + 24 GB RAM. Check free RAM and GPU power (`python scripts/doctor.py`) before model runs; one LLM loaded at a time.
- Do not `npm run build` the dashboard while a run is live (servers on 3000/3001 serve the old build).
- Long nested heredocs in the Bash tool fail; use Write/Edit. Use `C:\` paths for Windows Python + sqlite.
- Never print `.env` files unfiltered (a LangSmith key leaked that way once).
