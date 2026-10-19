# Phase 1a-0: Measure first

**Goal:** know where the pipeline actually fails, have the evals and the
scoreboard that will judge every later change, and a dev loop measured in
minutes, not hours. No big model needed.

**Depends on:** scope v2.2 locked; housekeeping commits (BUILD_ORDER sprint 0).
**Scope items:** P0.1-P0.5 (SCOPE section 7), S10-S12.

## Tasks

- [ ] **Error analysis (P0.1).** From the saved runs (archived reports + `logs/goal-slm.txt` evidence), sample ~50 claims. For each: verdict (ok / wrong) and, if wrong, the first stage that went wrong:
  `retrieval miss` (right source never found) · `bad source` (off-goal source used) · `extraction subject` (fact names the wrong system/size/stage) · `writing subject` (fact right, sentence drops or changes its subject; added 2026-10-19 while labelling) · `writing stitch` (facts from different sources joined) · `label` (wrong evidence label) · `other`.
  Labelled by the user and by Claude separately and **blind** (Claude's labels in `evals/error_analysis/claude_labels.csv`); disagreements discussed. Result: a breakdown table in `EVALS.md` and a re-prioritised 1b/1c task order.
- [ ] **Eval set (P0.2).**
  - Retrieval: existing `evals/retrieval_qa.json` re-run as the baseline.
  - Held-out goal (E-010): one gold goal the prompts were never tuned on, scored alongside the SLM goal.
  - Extraction: `evals/subject_facts.jsonl`, ~40 passage → expected (subject, size, stage) cases, including E7/E8, E79, E76/E40.
  - Writing: `evals/faithfulness_sheet.csv`; the user settles the 8 disputed labels (ids 2, 9, 11, 16, 25, 31, 34, 39).
  - LLM judge calibrated against the user's labels (agreement rate recorded; judge used only if ≥ 85%).
- [ ] **Scoreboard (P0.3).** One table in `EVALS.md`: rows = metrics (retrieval hit@k, subject accuracy, numbers traced, label errors, blind score, minutes per report); columns = v6 baseline, raw-passage baseline, then one column per phase gate. Script `scripts/scoreboard.py` fills what can be computed.
- [ ] **Dev loop (P0.4).**
  - Mini fixture: 1 question, 5 saved sources, committed under `tests/fixtures/mini/`; a run on it finishes in < 10 min with the current models.
  - Writing replay: re-run only the writing step from saved evidence (simple file-based version now; checkpoint fork comes in 1a).
  - Fact viewer: `scripts/fact_viewer.py` prints passage | fact | verdict side by side (markdown or HTML) for eyeballing.
- [ ] **Code audit (P0.5).** List of v1 modules the scope does not use (quick-research graph and its helpers, Profile, `/new`, `/profile`, `/compare`). The user decides keep or archive; archived code moves to `archive/v1-quick/` on a branch-free commit, tests moved with it.

## Test cases

| ID | Type | Case | Expected |
|---|---|---|---|
| P0-T01 | Manual | Error analysis sample | ≥ 50 claims labelled; stage breakdown sums to the wrong count |
| P0-T02 | Unit | Subject eval loader | All cases parse; E7/E8, E79, E76/E40 present |
| P0-T03 | Unit | Judge calibration script on a toy sheet | Agreement computed correctly |
| P0-T04 | Integration | Mini fixture run | Finishes < 10 min; produces a report and a run record |
| P0-T05 | Integration | Writing replay from saved evidence | Only the writing step runs (no fetch, no extraction calls) |
| P0-T06 | Unit | Scoreboard script | Reads eval outputs, writes the table, leaves missing cells as "—" |
| P0-T07 | Regression | Full offline suite after any archiving | Green; no import of an archived module remains |

## Review items
- The stage labels follow the first failure, not the most visible one.
- The scoreboard numbers are reproducible by a script, not typed by hand (except the blind score).

## Exit gate
- [ ] All test cases pass; full offline suite green.
- [ ] Error breakdown in `EVALS.md`; 1b/1c task order updated from it (noted in DECISIONS).
- [ ] Judge calibrated or explicitly not used.
- [ ] Code-audit decision recorded.

## Results
_Fill in at the gate._
