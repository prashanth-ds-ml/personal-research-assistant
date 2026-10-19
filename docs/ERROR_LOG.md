# Error log

Every bug, failed test and review finding: one entry each, newest first. An
entry is `closed` only when the fix is in and a regression test exists that
fails without it. Known issues from before scope v2 are seeded below so they
are tracked the same way.

## Index

| ID | Date | Phase | Severity | Found by | Title | Status |
|---|---|---|---|---|---|---|
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
