# Phase 4: Second domain + studio demo

**Goal:** show it works beyond AI/ML with one more domain, and package a
local-only demo.

**Depends on:** P3 gate. Decide the second domain at phase start (Q3).
**Scope items:** P4.1-P4.4.

## Tasks

- [ ] Domain pack format: fact fields, source lists, tiers, report templates; move AI/ML into it.
- [ ] Second domain pack (e.g. healthcare evidence or business/markets).
- [ ] Demo corpus per domain; one sample report + chat transcript each.
- [ ] Demo script: offline run, chat, report from library, evidence clicks; demo video.

## Test cases

| ID | Type | Case | Expected |
|---|---|---|---|
| P4-T01 | Unit | Pack validation | Broken pack fails at startup naming the file |
| P4-T02 | Regression | AI/ML via the pack | Same results as before the move |
| P4-T03 | Golden | Second domain: 1 report + 10 chat questions | Pass Phase 1/2 checks |
| P4-T04 | Manual | Demo script with network off | Runs end to end |

## Exit gate
- [ ] All test cases pass; SCOPE section 8 Phase 4 acceptance met; no open Critical/High errors.

## Results
_Fill in at the gate._
