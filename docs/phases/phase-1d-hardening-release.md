# Phase 1d: Hardening, dashboard, packaging → v1.0

**Goal:** a stranger can install it, run a report, and trust the result;
v1.0 tagged.

**Depends on:** P1c gate.
**Scope items:** P1.18 (kept), P1.19, P1.21, packaging; E-003..E-007.

## Tasks

- [ ] Live progress via `get_stream_writer` (custom stream); run record gets a single writer (E-003).
- [ ] Dead-Ollama check after early nodes (E-005); plan unchanged check on resume (E-006); LangSmith lookup off the report page's critical path (E-007).
- [ ] `durability="sync"` for research runs.
- [ ] Dashboard: commit and deploy the Research Desk redesign; collections in Library; limits and model roles in Settings; collected/read/used counts and source states shown on the run, report and Library pages.
- [ ] README rewrite: what it is, diagram, prerequisites (RAM/GPU, model sizes), quick start, honest limits; fix outdated notes (e.g. thread persistence).
- [ ] `make setup / doctor / models / dev / test` + Windows scripts; one Python version.
- [ ] Demo corpus (6-8 open-access AI/ML papers) + one committed sample report.
- [ ] CI: tests, lint, `langgraph dev` smoke, compose build.
- [ ] Move superseded planning docs to `docs/history/`.
- [ ] **Portfolio deliverables:** README hero (one sentence, GIF of claim → quote, honest hardware); committed sample report + run record; evals page from the scoreboard; case study (`docs/CASE_STUDY.md`: error analysis → simple baseline → what beat it, with numbers); architecture diagram.
- [ ] **Pre-publish clean-up:** rotate the LangSmith key; scan git history for secrets (e.g. `gitleaks`); no personal vault, Profile or archived reports in the repo; demo corpus licences checked.

## Test cases

| ID | Type | Case | Expected |
|---|---|---|---|
| P1d-T01 | Integration | Kill Ollama after planning | Clear error at the next model step; run marked failed, resumable |
| P1d-T02 | Integration | Edit plan state, then resume | Detected; user asked to confirm |
| P1d-T03 | Integration | Stop during reading | Stops within one call; run record consistent; resume works |
| P1d-T04 | Integration | Two runs at once (queued) | No shared state; both records correct |
| P1d-T05 | Manual | Dashboard click-through: new run, approve plan + rules, exclude a source, watch, read report, library, settings | No console errors; every button wired or marked "not wired" |
| P1d-T06 | Integration | Fresh clone on a clean venv following README | Report produced from the demo corpus |
| P1d-T07 | Blind quality | 3 gold goals (T1-T3) vs v6 baseline | v1.0 better on the checklist for all three |
| P1d-T08 | CI | Pipeline on push | Green |
| P1d-T09 | Security | Secret scan over full git history | No findings (or rotated and documented) |
| P1d-T10 | Manual | A reader who has not seen the project opens the README | Understands what it is and sees a claim → quote in under 2 minutes |

## Review items
- README makes no claim the tool does not meet (domains, speed, offline).
- Demo corpus licences allow redistribution.

## Exit gate (= v1.0)
- [ ] All test cases pass; SCOPE section 8 Phase 1 acceptance met.
- [ ] No open Critical/High errors; E-003..E-007 closed.
- [ ] Portfolio deliverables and clean-up done; scoreboard final column filled.
- [ ] Tag v1.0 (public release); demo video recorded.

## Results
_Fill in at the gate._
