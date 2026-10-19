# Error log

Every bug, failed test and review finding: one entry each, newest first. An
entry is `closed` only when the fix is in and a regression test exists that
fails without it. Known issues from before scope v2 are seeded below so they
are tracked the same way.

## Index

| ID | Date | Phase | Severity | Found by | Title | Status |
|---|---|---|---|---|---|---|
| E-015 | 2026-10-19 | M1 | High | M1 live run | Yes/no passage relevance made qwen3.5:4b reject almost everything (0 of 8 kept per question) | fixed |
| E-014 | 2026-10-19 | M1 | Medium | M1 live run | With thinking on, qwen3.5:4b returned an empty plan (56 s), so the run fell back to one question | fixed |
| E-013 | 2026-10-19 | P1a-0 | Low | S1 test | Labelling workbook dropdowns accepted any typed value (openpyxl turns the error alert off by default) | fixed |
| E-012 | 2026-10-19 | P1a-0 | Low | S0 review | `model_goal` keeps an unanswered clarifying question as if the user said it | open |
| E-011 | 2026-10-19 | P1c | Low | S0 review | Filler-sentence removal can split numbered list items ("1. The table shows…" leaves "1.") | open |
| E-010 | 2026-10-19 | P1a-0 | Medium | S0 review | Prompts carry examples from one test goal (4B-8B models, speech/hate-speech) | open |
| E-009 | 2026-10-19 | P1a | Low | test warnings | LangGraph `config_schema` deprecated (`graph.py:836`) | open |
| E-008 | 2026-10-19 | P1a-0 | Low | test warnings | `langchain-community` is being sunset; still imported by `utils.py:7` (SearxSearchWrapper) | open |
| E-007 | 2026-10-01 | P1d | Medium | close-out review | LangSmith lookup blocks the report page | open |
| E-006 | 2026-10-01 | P1d | Medium | close-out review | Resume does not check the plan is unchanged | open |
| E-005 | 2026-10-01 | P1d | High | close-out review | Dead Ollama passes plan/coverage/discover silently | open |
| E-004 | 2026-10-01 | P1d | High | close-out review | Global STOP / LLM_STATS shared across runs | open |
| E-003 | 2026-10-01 | P1d | Medium | close-out review | Run record has two writers | open |
| E-002 | 2026-10-03 | P1b | Medium | report review | Garbled characters (`�`) in titles and claims | open |
| E-001 | 2026-10-03 | P1b/P1c | Critical | report review | Claims take the question's wording, not the source's subject; numbers from different papers stitched and labelled "established" | open |

## Entry template

```markdown
### E-000: <short title>

- **Date found:** YYYY-MM-DD
- **Phase:** P<n>
- **Severity:** Critical | High | Medium | Low
- **Found by:** test <ID> | review | eval | live run | demo
- **Status:** open | fixing | closed | won't fix (reason)

**What happened:** observed vs expected; exact error; input that triggers it.
**Root cause:** why, not just where.
**Fix:** what changed.
**Regression test:** test ID that now guards it.
**Pattern?** Which REVIEW_CHECKLIST item should have caught it, or which to add.
```

## Entries

### E-015: A yes/no relevance question made the small model reject nearly every passage

- **Date found:** 2026-10-19 · **Phase:** M1 · **Severity:** High · **Found by:** second v3 live run · **Status:** fixed

**What happened:** questions 1-3 kept 0 of 8 passages each. A probe showed the answers parsed fine and were all `false`,
including a related fine-tune model card, also after loosening the wording.
**Root cause:** qwen3.5:4b leans to "no" on a binary usefulness question.
**Fix:** a 0-3 grade (3 answers directly, 2 specific related information, 1 same field only, 0 unrelated/other modality);
passages scoring 2+ are kept (`MIN_PASSAGE_SCORE`). On the same passages the grade kept 3 of 6 for the tool-calling question
and none for the data question, where the library really lacks Telugu pretraining-data sources.
**Regression test:** `test_M1_T09_passage_score_threshold_and_unreadable_answers`.
**Pattern?** Ask a small model for a grade, not a verdict; probe a judge on real passages before a full run.

### E-014: Thinking mode emptied the plan

- **Date found:** 2026-10-19 · **Phase:** M1 · **Severity:** Medium · **Found by:** first v3 live run · **Status:** fixed

**What happened:** the first v3 run planned "1 question, 2 sections" after 187 s. The planner (qwen3.5:4b, `reasoning=True`,
JSON mode) returned an empty answer, so `make_plan` fell back to the goal as the only question. A direct probe: thinking on,
56 s and 0 characters; thinking off, 8 s and a valid plan with 5 questions and 6 sections.
**Root cause:** the model spent the output on thinking (or thinking does not combine with JSON mode in this setup); the
answer itself was empty. The fallback hid it as a thin plan instead of failing.
**Fix:** thinking off in every role (`build_llms`, `run_deep_report.py`).
**Regression test:** `test_M1_T08_one_model_in_every_role_thinking_off`.
**Pattern?** A silent fallback turns a model failure into a plausible-looking result; the plan size in the log was the only sign.
Consider failing loudly when the planner returns nothing (backlog).

### E-013: Labelling workbook dropdowns accepted any typed value

- **Date found:** 2026-10-19 · **Phase:** P1a-0 · **Severity:** Low · **Found by:** Sprint 1 test (adding note dropdowns) · **Status:** fixed

**What happened:** the verdict and stage dropdowns in `claims.xlsx` offered the right values, but a typed value outside the list
(e.g. "wrnog") was accepted, so the "cannot be mistyped" promise did not hold. `tally` would have raised on an unknown stage later.
No labels had been entered yet.
**Root cause:** openpyxl's `DataValidation.showErrorMessage` defaults to False; the old test only counted the validations.
**Fix:** `write_label_workbook` sets `showErrorMessage` on for verdict and stage (off for the note column, which offers
suggestions only); the workbook was rebuilt with the same sample (claims.csv byte-identical).
**Regression test:** `test_labelling_workbook_round_trip` checks the error alert is on for verdict/stage, off for note, and that
every label cell has pop-up help within Excel's 255-character limit.
**Pattern?** Test the behaviour a setting promises, not that the setting object exists.

### E-012: `model_goal` keeps an unanswered clarifying question as if the user said it

- **Date found:** 2026-10-19 · **Phase:** P1a-0 · **Severity:** Low · **Found by:** Sprint 0 review · **Status:** open

**What happened:** `deep_report.model_goal` treats a clarification line as the assistant's question only when the next line is a
`->` answer. If an unanswered question were present, it would be passed to the models as a user statement: the drift the function
exists to prevent. Today the dashboard omits unanswered questions (see `goal_graph.qa_pairs`), so it does not trigger.
**Root cause:** the parser depends on the dashboard's text format rather than on structured clarification data.
**Fix:** pass clarifications as structured `{question, answer}` pairs (already recorded in the run record) instead of re-parsing text.
**Regression test:** to add (P1a-0): goal text with an unanswered question → not in the model goal.
**Pattern?** Do not re-parse text we generated ourselves; keep the structure.

### E-011: Filler-sentence removal can split numbered list items

- **Date found:** 2026-10-19 · **Phase:** P1c · **Severity:** Low · **Found by:** Sprint 0 review · **Status:** open

**What happened:** `_drop_filler_sentences` splits on `(?<=[.!?])\s+(?=[A-Z])`. A list item such as "1. The table shows …" splits
after "1." and the filler part is dropped, leaving a bare "1.". Also rejoins split lines with single spaces.
**Fix:** skip list markers when splitting, or drop the whole list item; revisit when Sprint 8 rewrites writing.
**Regression test:** to add (P1c).

### E-010: Prompts carry examples from one test goal

- **Date found:** 2026-10-19 · **Phase:** P1a-0 · **Severity:** Medium · **Found by:** Sprint 0 review · **Status:** open

**What happened:** the October fixes add concrete examples to general prompts: "4B-8B generative model", "200M-parameter encoder",
"speech or hate-speech detection", "pretraining or fine-tuning". They came from the SLM gold goal. They may bias other goals
(the product is meant to work on any topic in the domain, and later other domains) and they make the SLM eval look better than a
new goal would.
**Root cause:** prompt fixes tuned on the failing goal, with no held-out goal to check against.
**Fix:** in Sprint 1 add a held-out goal to the eval set; in Sprint 6/8 replace goal-specific examples with field-based rules
(system / size / stage) and neutral examples. Measure before and after on both goals.
**Regression test:** held-out goal on the scoreboard (P1a-0).
**Pattern?** Add checklist item: "a prompt fix is checked on a goal it was not tuned on".

### E-009: LangGraph `config_schema` deprecated

- **Date found:** 2026-10-19 · **Phase:** P1a · **Severity:** Low · **Found by:** test warnings · **Status:** open

**What happened:** `LangGraphDeprecatedSinceV10: config_schema is deprecated … use context_schema` at `graph.py:836` (removed in V2.0).
**Fix:** Sprint 3 moves run options to `context_schema` (with E-004). If the v1 quick mode is archived in Sprint 2, this warning goes with it.

### E-008: `langchain-community` sunset

- **Date found:** 2026-10-19 · **Phase:** P1a-0 · **Severity:** Low · **Found by:** test warnings · **Status:** open

**What happened:** `utils.py:7` imports `SearxSearchWrapper` from `langchain_community`, which is no longer maintained.
**Fix:** archived with the v1 quick mode (Sprint 2 decision), or replaced with a direct SearXNG HTTP call (the collector already has
one in `collector.searxng_search`).

### E-001: Claims take the question's wording, not the source's subject

- **Date found:** 2026-10-03 · **Phase:** P1b (subject), P1c (provenance, labels) · **Severity:** Critical · **Found by:** report review · **Status:** open

**What happened:** E7/E8 "optimal hyperparameters for pretraining a 4B model
from scratch" came from a post-training evaluation paper; E79 "pretraining a
4B model … 22.63T tokens" came from a 17B model card; E76/E40 came from a
fine-tuned model card. The summary stitched four sources' numbers into one
sentence labelled [established].
**Root cause:** extraction phrases facts in the question's terms; checks
verify the quote is verbatim, not that the claim's subject matches the
source; labels did not require agreement between documents.
**Fix:** planned in Phase 1b (structured facts + field-based subject check)
and Phase 1c (number provenance, label rules).
**Regression test:** P1b-T01..T04, P1c-T04..T06.
**Pattern?** Add checklist item: "a check must test meaning (subject), not
only form (verbatim quote)".

### E-002 to E-007

Details in `docs/closeout-review-2026-10-01.md` and `docs/next-steps.md`;
expand each entry when its phase starts.
