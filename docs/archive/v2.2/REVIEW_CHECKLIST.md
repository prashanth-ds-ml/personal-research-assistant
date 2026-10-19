# Review checklist (every phase)

Any "no" becomes an ERROR_LOG entry.

## Claim correctness
- [ ] Every claim names its real subject as the source does (system, size, stage); the check compares fields, not prose.
- [ ] Every number traces to exactly one fact; no sentence mixes numbers from different sources unless labelled synthesis.
- [ ] Labels follow the rules: established = ≥2 agreeing documents; single source; synthesis; inference.
- [ ] Gaps are stated in the report and in chat; nothing is filled from general model knowledge.
- [ ] Checks test meaning (subject, support), not only form (verbatim quote, JSON shape).
- [ ] A gate looks at what was actually written, not only at what evidence existed.
- [ ] A prompt fix is checked on a goal it was not tuned on (held-out goal), not only on the failing one.

## Budgets and limits
- [ ] Every prompt has a token budget and stays within it (logged).
- [ ] Nothing is cut silently: collected / read / used counts and not-read / not-used lists in the run log and report.
- [ ] Run limits come from configuration (runtime context), not constants or globals.

## Robustness
- [ ] Ollama down / slow / out of memory gives a clear message, never a silent pass or hang.
- [ ] Resume after crash or Stop continues from the last checkpoint without redoing finished work.
- [ ] Timeouts are not retried; connection errors are (RetryPolicy).
- [ ] Messy inputs tested: garbled text, scanned PDFs, duplicate versions, off-goal sources.

## Library and data
- [ ] Nothing in the library or vault is deleted (removal moves to `.removed`).
- [ ] Facts and sources are stored with provenance (source, passage, run, model, prompt version).
- [ ] Collections stay separate; a run or chat only uses its collection unless told otherwise.

## Design discipline
- [ ] Only the phase scope was built.
- [ ] Framework features used where FRAMEWORK_FIT.md says; no new hand-rolled version of a built-in.
- [ ] Research stays an explicit graph; agent loops only in chat.
- [ ] Local only: no cloud calls by default (LangSmith off unless explicitly enabled).

## Tests and docs
- [ ] All phase test cases exist and pass; the full offline suite passes.
- [ ] One real report (or chat transcript) read end to end by a person.
- [ ] Everything automatable was tested by Claude (live model, API, Playwright where relevant), not left to the user.
- [ ] Blocking user tests in USER_TESTS.md passed; failures logged.
- [ ] STATUS.md, phase Results, DECISIONS.md, EVALS.md, CASE_STUDY.md sprint log updated.
