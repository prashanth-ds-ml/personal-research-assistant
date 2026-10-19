# How we build: one phase at a time

Scope: `SCOPE.md` (v2.2). Status: `STATUS.md`. Order: `BUILD_ORDER.md` (sprints). Every phase (and Phase 1 sub-phase)
runs the same loop, and the next one starts only after the gate passes.

```
 Plan ──► Tests first ──► Build ──► Run ALL tests ──► Review ──► Gate
                                        │ fail          │ finding    │ fail
                                        ▼               ▼            │
                                  ERROR_LOG entry → fix → regression test ─► back to "Run ALL tests"
```

## Steps

1. **Plan.** Re-read the phase doc in `docs/phases/`. Resolve the open
   decisions it depends on (entry in `DECISIONS.md`). Set the phase to
   `in progress` in `STATUS.md`.
2. **Tests first.** Turn the phase's test-case table into tests before the
   feature code. Name tests by ID: `test_P1b_T03_subject_size_mismatch_dropped`.
   Report-quality cases use **saved runs** (forked checkpoints, saved
   evidence files) so they are repeatable without re-reading sources.
3. **Build** only the phase scope. Ideas go to the STATUS.md backlog.
4. **Run all tests**: offline suite every time; live/model tests at the gate.
5. **Review** with `REVIEW_CHECKLIST.md` plus the phase's review items, a
   code-review pass, and **reading one real report end to end**.
6. **Gate.** Exit criteria met, blocking user tests passed, no open
   Critical/High errors for the phase, Results section filled in, `STATUS.md`
   updated, measurements in `EVALS.md`, sprint log in `CASE_STUDY.md`.
7. Every failure or finding → `ERROR_LOG.md` → fix → regression test.

## Branches

One branch per phase (`phase-1a0`, `phase-1a`, …), merged into `main` at the phase gate, so `main` always holds a passed gate.

## Testing split: test everything possible

| Who | Tests | Where tracked |
|---|---|---|
| 🤖 Claude | Everything automatable or scriptable: unit, integration, golden, adversarial, budget, performance, live Ollama runs, API calls, dashboard end-to-end (Playwright, headless), lint, type check, secret scan, fresh-clone install; independent second labels on evals | Test files by ID; results in phase Results and `EVALS.md` |
| 🧑 User | Human judgement (blind scoring, labels), real daily use, UI feel, machine (RAM, power), accounts (keys), decisions, fresh-eyes reading | `docs/USER_TESTS.md` (status + notes) |

A blocking user test must pass before its sprint gate. A failed user test
gets an ERROR_LOG entry like any other failure.

## Severity

| Level | Meaning in this project | Gate rule |
|---|---|---|
| Critical | A wrong claim presented as supported (wrong subject, stitched numbers, invented number, "established" without two agreeing sources); data loss in the library/vault; secret leaked | Blocks the gate |
| High | In-scope feature broken; run crashes or hangs on a realistic goal; silent truncation; a gap hidden instead of stated | Blocks the gate |
| Medium | Works but degraded: slow beyond estimate, weak prose, confusing message, edge case with a clear warning | Passes only if listed in Results with an owner |
| Low | Cosmetic, wording | Does not block |

## Test types

| Type | Proves | Example |
|---|---|---|
| Unit | One function | Subject check rejects "4B" when the passage says 17B |
| Golden (saved evidence) | Output on fixed evidence meets the bar | Forked SLM run: no stitched numbers in the decision |
| Integration | Graph flow | Plan → approve → read (Send) → select → write → report saved |
| Adversarial | Bad input fails safely | Off-goal source, empty library, Ollama down, garbled PDF |
| Budget | Context limits hold | No prompt over its token budget; set-aside list present |
| Blind quality | Human judgement, not self-scoring | Reports scored blind on the checklist vs the v6 baseline |
| Performance | Time and memory | Model fits without paging; minutes per step recorded |

## Files

| File | Purpose |
|---|---|
| `docs/SCOPE.md` | What we build and why (v2.2) |
| `docs/FRAMEWORK_FIT.md` | Which LangChain/LangGraph features to use where |
| `docs/STATUS.md` | Current phase, gates, blockers, backlog |
| `docs/BUILD_ORDER.md` | Sprints in order, who tests what, gates |
| `docs/USER_TESTS.md` | Tests only the user can do, with status |
| `docs/CASE_STUDY.md` | Living case study: sprint log every sprint, final form at v1.0 |
| `docs/phases/*.md` | Scope, tasks, test cases, review items, gate, results per phase |
| `docs/ERROR_LOG.md` | Every bug/finding with cause, fix, regression test |
| `docs/REVIEW_CHECKLIST.md` | Questions applied to every phase |
| `DECISIONS.md` | Decisions and debugging notes (append-only) |
| `EVALS.md`, `BENCHMARKS.md` | Measurements, whatever they show |
| `CLAUDE.md` | Rules for Claude in this repo |
