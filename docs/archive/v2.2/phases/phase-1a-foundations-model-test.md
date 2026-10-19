# Phase 1a: Foundations + model test

**Goal:** choose the research model on evidence, and put in place the
foundations every later sub-phase uses (run options, saved-evidence
harness, memory preflight).

**Depends on:** P1a-0 gate (error analysis, evals, dev loop); reboot (free RAM); GPU power cap fixed.
**Scope items:** P1.1, P1.20, run-options part of P1.2, E-004 (globals).

## Tasks

- [ ] Add `langgraph-checkpoint-sqlite` dependency (lock update as its own commit).
- [ ] `RunOptions` runtime context (`context_schema`): limits L1-L8, collection, model roles, num_ctx; replaces globals and per-run config in state.
- [ ] Saved-evidence harness: save a run's selected evidence + plan (and use checkpoint fork via `get_state_history` / `checkpoint_id`) so the writing step can be replayed with any model.
- [ ] Re-run the saved SLM goal (`logs/goal-slm.txt`) once with the current pipeline to produce the baseline evidence set.
- [ ] Verify with gemma4:26b-a4b: `with_structured_output(method="json_schema")` works; thinking on/off parameter in langchain-ollama 1.1.0; 32k `num_ctx` loads once.
- [ ] Doctor: free RAM vs model size, GPU power limit, warn when the model would page; `OLLAMA_MAX_LOADED_MODELS=1`.
- [ ] Pull candidates (check the exact tags exist first); run the model test (SCOPE section 9, runs 1-6) on identical evidence.
- [ ] Raw-passage baseline writer (P1.27): retrieve → best raw passages into 32k → write with quotes; run 7 with the winning model.
- [ ] Critique on/off (run 8) with the winning model; result decides whether S7 stays.
- [ ] Scoreboard columns filled for every run.
- [ ] Blind scoring sheet (subjects, numbers, decision, repetition, readability), scored by the user (and Claude separately); results in `EVALS.md`.

## Test cases

| ID | Type | Case | Expected |
|---|---|---|---|
| P1a-T01 | Unit | RunOptions defaults and overrides | Limits come from context; no module-level state used by nodes |
| P1a-T02 | Integration | Two runs with different limits in the same server | Each run uses its own limits (fixes E-004) |
| P1a-T03 | Integration | Fork a saved run at the writing step with another model | Writing re-runs; reading does not; same evidence used |
| P1a-T04 | Unit | Structured output with gemma4:26b on 5 extraction samples | Valid schema objects; failures logged, not crashed |
| P1a-T05 | Performance | Each candidate at 32k | Fits without paging (doctor check); minutes per step recorded |
| P1a-T06 | Blind quality | Model test reports | Scores recorded; winner chosen by rule (best score; tie → faster) |
| P1a-T07 | Unit | Doctor with insufficient RAM (mocked) | Clear warning naming the model and the shortfall |
| P1a-T08 | Golden | Raw-passage baseline on saved SLM evidence | Report produced; scored blind with the others; scoreboard column filled |
| P1a-T09 | Blind quality | Winner with vs without one critique round | Scores recorded; S7 kept only if the critique version scores higher |

## Review items
- The test used identical evidence for every model (fork, not re-run).
- Scoring was blind (model names hidden).

## Exit gate
- [ ] All test cases pass; full offline suite green.
- [ ] Research model decided (DECISIONS entry); raw-passage baseline and critique results recorded; scoreboard updated.
- [ ] Measured minutes per step replace the L10 estimate in SCOPE.
- [ ] No open Critical/High errors for P1a.

## Results
_Fill in at the gate._
