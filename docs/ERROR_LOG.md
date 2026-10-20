# Error log

Every bug, failed test and review finding: one entry each, newest first. An
entry is `closed` only when the fix is in and a regression test exists that
fails without it. Known issues from before scope v2 are seeded below so they
are tracked the same way.

## Index

| ID | Date | Phase | Severity | Found by | Title | Status |
|---|---|---|---|---|---|---|
| E-020 | 2026-10-20 | M3 | Low | long-report test | Sentence split at "(approx." misplaced a label | fixed |
| E-019 | 2026-10-20 | M3 | High | long-report test | Plan missed 2 of 6 goal topics and added malformed catch-all questions | fixed |
| E-018 | 2026-10-19 | M2 | Medium | Test A | One embedding request per document (hundreds of chunks) made Ollama's runner fail | fixed |
| E-017 | 2026-10-19 | M2 | Medium | chunk-size check | Table splitter repeated a giant header, so pieces exceeded the limit (7,159 chars); a 2,190-char heading was prefixed to chunks | fixed |
| E-016 | 2026-10-19 | M2 | Medium | backend start | Backend would not start: shared venv had opentelemetry-api 1.45.1 with SDK 1.42.1 | worked around |
| E-015 | 2026-10-19 | M1 | High | M1 live run | Yes/no passage relevance made qwen3.5:4b reject almost everything (0 of 8 kept per question) | fixed |
| E-014 | 2026-10-19 | M1 | Medium | M1 live run | Thinking at temperature 0 never finished (qwen3.5:4b), so the plan fell back to one question | fixed |
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

### E-020: A bracketed abbreviation ended a sentence

- **Date found:** 2026-10-20 · **Phase:** M3 · **Severity:** Low · **Found by:** reading the long-report test · **Status:** fixed

**What happened:** "qwen3.5:9b-q4_K_M (approx. 6.6 GB VRAM)" was split after "(approx.", so a label landed mid-sentence.
**Root cause:** the abbreviation check compared "(approx." with "approx.". **Fix:** leading brackets and quotes are ignored
(also ca., cf.). **Regression test:** `test_V3_T08_an_abbreviation_after_a_bracket_does_not_end_the_sentence`.

### E-019: The plan misses goal topics and adds malformed catch-all questions

- **Date found:** 2026-10-20 · **Phase:** M3 · **Severity:** High · **Found by:** long-report test (3 runs) · **Status:** fixed

**What happened:** the goal named six topics (embedding models, chunking, hybrid search, reranking, evaluation, running on
an 8 GB GPU). The plan asked about four; chunking and evaluation got no question although the library held an evaluation
guide. Two questions added by `add_missing_topics` were "What does the evidence say about Building a private RAG system"
and "... about for a small team", which retrieved nothing and became empty gap sections.
**Root cause (confirmed from the run trace):** the planner DID ask about chunking and evaluation; the scope judge
removed both as "not needed" although the goal names them. The missing-topic step then took the goal's overall subject
("Building a private RAG system") and a qualifier ("for a small team") as topics and filled its two slots with template
questions. **Fix:** the goal's topics are listed once (`goal_topics`: verbatim, no qualifiers, not the subject before the
colon, leading "and/or" trimmed); a question covering one of them is never sent to the scope judge; a missing topic gets a
real question written by the model, which first says whether an existing question already covers it in other words.
Live: the same goal now plans 6 questions, one per topic, nothing dropped, no filler, no duplicate.
**Regression tests:** `tests/test_planner_topics.py` (P_T01-P_T06). **Pattern?** Report quality is capped by the plan;
check the plan as strictly as the text.

### E-018: One embedding request per document made Ollama's embedding runner fail

- **Date found:** 2026-10-19 · **Phase:** M2 · **Severity:** Medium · **Found by:** Test A (re-embedding at 600-char chunks) · **Status:** fixed

**What happened:** `POST /api/embed` returned 400 after ~12 s ("connection refused" on the runner's /tokenize); retries hit a
new runner and failed the same way. **Root cause:** `ingest_text` and `rebuild` sent all of a document's chunks in one
request; at small chunk sizes a big PDF is hundreds of chunks. The real library had not hit it yet (fewer chunks at 1,800).
**Fix:** `KnowledgeBase._embed` sends batches of 32 with retries. **Regression test:** `test_K_T04_embedding_goes_in_batches`.
**Pattern?** Bound every request a batch job sends to a local service.

### E-017: Chunks over the limit: giant table headers and a giant heading

- **Date found:** 2026-10-19 · **Phase:** M2 · **Severity:** Medium · **Found by:** checking library uniformity before locking the chunk size · **Status:** fixed

**What happened:** 82 of 5,102 chunks exceeded their limit; the worst, 7,159 characters, appeared four times. **Root cause:**
`_split_table` repeats the header in every piece without bounding it (one TransMI table had a 2,332-character header line),
and the heading path prefixed to chunks was unbounded (a broken PDF heading of 2,190 characters). **Fix:** header at most a
third of a piece, rows cut to fit; heading path capped at 300; library re-chunked under the locked v2 settings (0 over).
**Regression tests:** `test_K_T01_...`, `test_K_T05_...`. **Pattern?** A limit must bound every part of what it limits.

### E-016: The backend would not start after another install changed the shared venv

- **Date found:** 2026-10-19 · **Phase:** M2 · **Severity:** Medium · **Found by:** starting `langgraph dev` · **Status:** worked around

**What happened:** `langgraph dev` failed with `ImportError: cannot import name '_ExtendedAttributes' from 'opentelemetry.util.types'`.
**Root cause:** on 2026-10-10 an install into the shared root venv (a newer fastapi needs `opentelemetry-api>=1.44`) raised
`opentelemetry-api` to 1.45.1 and left the SDK and exporters at 1.42.1, which do not import together. `langgraph-api 0.15.1`
declares the 1.42 family (Prometheus exporter <0.64), so no set satisfies every declared range.
**Fix (work-around):** aligned the whole OpenTelemetry family at 1.45.1 / 0.66b1; the backend starts and a full run passes.
`uv pip check` still reports langgraph-api's declared range. Proper fix later: a newer langgraph-api, or a project venv.
**Regression test:** none automatic; `python scripts/doctor.py` could import `langgraph_api.server` (backlog).
**Pattern?** A shared venv lets another project break this one silently; check the backend starts after any shared install.

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
**Root cause (corrected after a second probe, same day):** greedy decoding. At temperature 0 the model thinks without end:
4,200 and 12,000-token budgets were both used up by thinking (16k / 45k characters, mostly re-checking a finished draft) and
no answer came, with or without JSON mode. With Qwen's recommended thinking settings (temperature 0.6, top_p 0.95, top_k 20)
it finished in 82-93 s (6-7k tokens) with a good 5-6-question plan; without thinking at temperature 0: 8 s, similar plan.
The fallback hid the failure as a thin plan instead of failing.
**Fix:** thinking off in every role (`build_llms`, `run_deep_report.py`). Thinking for planning only, with Qwen's
sampling settings, is possible (~85 s per plan, plans vary between runs); left to the user's choice.
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
