# Tests only you can do

Claude runs every test that can be automated or scripted (see "Testing split"
in `docs/PROCESS.md`). This file lists the ones that need **you**: human
judgement, real daily use, how it feels to use, your machine, your accounts,
and fresh eyes. Claude keeps it current; you tick and add notes.

**Status:** `todo` → `doing` → `pass` / `fail` (a fail gets an ERROR_LOG entry) · `n/a`
**Blocking:** a blocking test must pass before its sprint's gate.

## Can do now, in parallel with any sprint

| ID | Test | How | Expected | Blocking | Status | Notes |
|---|---|---|---|---|---|---|
| U-P1 | Rotate the LangSmith key | LangSmith → Settings → API keys: revoke the old key, make a new one, put it in `dashboard/.env.local` (don't paste it into chat) | Old key revoked | S11 | todo | |
| U-P2 | Label 20 faithfulness rows, blind | Open `evals/faithfulness_human.csv` (20 shuffled rows: the 8 disputed ones + 12 random; the judge's and Claude's verdicts are hidden). For each row read `context`, then put `y` in `human` if it supports `claim`, `n` if not; `note` optional. Then `python scripts/judge_calibration.py` | All 20 labelled; judge agreement with you computed (≥ 85% to use the judge) | S1 | todo | Grew from 8 to 20 on 2026-10-19: with only the disputed rows the agreement number would be circular |
| U-P3 | Memory routine | Find which apps to close for ≥ 12 GB free; run `python scripts/doctor.py` | You know the routine before Sprint 4 | S4 | todo | Edge, extra Claude windows, Unsloth Studio (:8888) |
| U-P5 | Choose the held-out goal (E-010) | A research question you'd really ask, not about small-model pretraining or Indic LLMs (e.g. a RAG, agents, evals or inference-cost question) | One goal written into `docs/phases/phase-1a0-measure-first.md` | S2 | todo | Used to check prompt fixes on a goal they were not tuned on |
| U-P4 | Current dashboard look-around | Open http://localhost:3001, try every page, note what looks broken or confusing | List of issues → ERROR_LOG / backlog | no | todo | Old build; for baseline impressions |

## Per sprint

| ID | Sprint | Test | How | Expected | Blocking | Status | Notes |
|---|---|---|---|---|---|---|---|
| U-01 | S0 | Read the October code-fix review | Claude's summary before the commit | You agree with keep / change | yes | pass | 2026-10-19: keep the helpful fixes; all kept |
| U-02 | S1 | Label 50 claims, blind | Read `evals/error_analysis/claims.md` (each claim with its facts, quotes and passages); fill `human_verdict` (ok / wrong), `human_stage` (first stage that went wrong: retrieval miss / bad source / extraction subject / writing subject / writing stitch / label / other) and `human_note` in `evals/error_analysis/claims.csv`. Claude's labels are in a separate file, don't open `claude_labels.csv` until you're done. Then `python scripts/error_analysis.py tally` | All 50 labelled; agreement with Claude computed; disagreements discussed | yes | todo | ~2 h. Rule of thumb: judge the claim as a reader of the report would; check the sentence before it if it says "the model" |
| U-03 | S2 | Fact viewer readable? | Open its output on the mini fixture | You can judge a fact in < 30 s | no | todo | |
| U-04 | S2 | Keep or archive v1 quick mode | Decide; if archived, click through the remaining dashboard pages | Decision recorded; nothing you use is gone | yes | todo | |
| U-05 | S4 | Free RAM before model runs | U-P3 routine; doctor shows ≥ 12 GB free | Doctor OK | yes | todo | |
| U-06 | S4 | Blind-score the model-test reports | Reports with names hidden; checklist: subjects, numbers, decision, repetition, readability | Scores in EVALS.md | yes | todo | ~3 h |
| U-07 | S4 | Read the winning report end to end | — | Would you trust and use it? Notes in EVALS.md | no | todo | |
| U-08 | S5 | Real wide collection on a topic you care about | Dashboard: approve plan + rules, exclude a source, watch | Counts make sense; Library shows states and origin | yes | todo | |
| U-09 | S5 | Spot-check 10 collected sources | Library | Tiers right; no junk or duplicates | no | todo | |
| U-10 | S6 | Hand-check 30 facts | Fact viewer, with Claude | 0 subject violations | yes | todo | |
| U-11 | S7 | Use the chat preview daily for a week | Your real questions | Annoyances listed in the Phase 2 doc | yes | todo | |
| U-12 | S7 | Try to break the chat | Out-of-library, vague, trick and number questions | Refuses or cites; never invents | no | todo | |
| U-13 | S8 | Read a full report end to end | Gold goal T1 | Decision sensible; numbers believable | yes | todo | |
| U-14 | S9 | Claim check click-through | Sample report: click 20 claims | Every click lands on the right highlighted quote | yes | todo | |
| U-15 | S10 | Dashboard full click-through | Every page and button | No dead buttons (or marked "not wired") | yes | todo | |
| U-16 | S10 | Failure handling from the UI | Stop a run, resume; quit Ollama mid-run | Clear message; resume works | yes | todo | |
| U-17 | S11 | Decide public vs private repo | — | Decision recorded | yes | todo | |
| U-18 | S11 | Blind-score 3 gold goals vs v6 | Names hidden | v1.0 better on all three | yes | todo | |
| U-19 | S11 | Fresh-eyes README test | Ideally someone else (e.g. a colleague) reads the README cold | Understands it and sees claim → quote in < 2 min | yes | todo | |
| U-20 | S11 | Record the demo video | Script from Claude | ≤ 3 min video | yes | todo | |
