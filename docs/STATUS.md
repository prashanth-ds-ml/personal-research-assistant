# Status

**Current phase:** Sprint 0 (housekeeping) in progress, 2026-10-19 → then Phase 1a-0 (Sprints 1-2)
**Last updated:** 2026-10-19
**Build order:** [BUILD_ORDER.md](BUILD_ORDER.md) · **Your tests:** [USER_TESTS.md](USER_TESTS.md) · **Case study:** [CASE_STUDY.md](CASE_STUDY.md)

| Phase | Doc | Status | Gate passed | Open Critical/High |
|---|---|---|---|---|
| 1a-0 Measure first | [phase-1a0](phases/phase-1a0-measure-first.md) | Sprint 0 in progress | — | 0 |
| 1a Foundations + model test | [phase-1a](phases/phase-1a-foundations-model-test.md) | not started | — | 1 (E-004) |
| 1b Collecting + reading + chat preview | [phase-1b](phases/phase-1b-reading.md) | not started | — | 1 (E-001) |
| 1c Writing + claim check view | [phase-1c](phases/phase-1c-writing.md) | not started | — | (E-001) |
| 1d Hardening + v1.0 | [phase-1d](phases/phase-1d-hardening-release.md) | not started | — | 1 (E-005) |
| 2 Chat | [phase-2](phases/phase-2-chat.md) | not started | — | 0 |
| 3 Compounding | [phase-3](phases/phase-3-compounding.md) | not started | — | 0 |
| 4 Domains + demo | [phase-4](phases/phase-4-domains-demo.md) | not started | — | 0 |

Statuses: `not started` → `in progress` → `testing` → `review` → `fixing` → `done`

## Blocked on (user)

- Free RAM before model runs (sprint 3): 4.9 GB free on 2026-10-19 even after a reboot; target ≥ 12 GB (close Edge, extra Claude windows, Unsloth Studio on :8888).
- Settle the 8 disputed faithfulness labels (sprint 1; blocks judge calibration).
- ~~Disk space for candidate models~~: 139 GB free on 2026-10-18, fine. GPU limit 115 W on 2026-10-18, fine; free RAM still 4.3 GB.

## Carried over from before scope v2 (user-owned)

- Rotate the LangSmith key in `dashboard/.env.local` (printed once in an earlier session).
- Check the 8 contestable faithfulness labels (`evals/faithfulness_sheet.csv` ids 2, 9, 11, 16, 25, 31, 34, 39).
- Uncommitted dashboard redesign in `dashboard/` (commit in Phase 1d).

## Backlog

See SCOPE section 11. New ideas land here with the evidence that motivates them.
