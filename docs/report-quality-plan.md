# Report quality plan (drafted 2026-10-01)

**Progress:** stages 0, 1 and 2 are built, tested (250 offline tests) and live-checked on the real goal (the coverage check
rated 12 questions: 1 answered, 7 thin, 4 nothing, which matches why the original report was poor). Stages 3-8 are next.

**Change made while building stage 0:** the plan said to exclude the whole `Sources/` folder from deep research. The library
report showed that 65 of its 84 documents are real archived web pages (good evidence, and much of what the tokenizer and Indic
questions rely on); only the 18 archived copies of local documents (`doc://`) are junk. So only those are left out by default
(`include_archived_pages` brings them back). Also: the start form no longer has a *collect sources* checkbox; the choice is made
at plan approval, next to the coverage.

Source: the review in `report-review-2026-10-01.md` (a real report that was confident, uncited in places, self-contradicting and
built on a library that did not cover the goal). Goal of this plan: the assistant either gives a report you can rely on, or
says plainly why it cannot, *before* it spends an hour.

Models: planning and extraction stay on `llama3.1:8b`; writing uses `gemma4:e4b` (`WRITER_MODEL`). On the 8 GB GPU only one
model is loaded at a time, so a run swaps once (llama -> gemma at the write step, about half a minute). Short JSON judgements
(coverage, relevance, consistency) use llama; prose uses gemma.

## Principles
1. **Check before spending.** Tell the user what the library can and cannot answer at plan approval, not after the report.
2. **Relevant, not just true.** A fact must be on topic for its question to count as evidence.
3. **Don't write what the evidence cannot carry.** Thin sections become short, honest gap notes, not filler.
4. **One answer, stated once.** Summary and recommendations come from the same decision; numbers must come from evidence.
5. **Everything deterministic that can be.** Counting, labelling, de-duplicating and grouping are code, not model calls.

## Stages (each: tests first, commit, then the next)

| # | Stage | What changes | Main files | Size |
|---|---|---|---|---|
| 0 | **Writer model and library hygiene** | `WRITER_MODEL=gemma4:e4b` (env, `.env.example`, compose default). Deep research ignores `Sources/` (archived quick-research pages) unless *Include archived pages* is ticked; the quick assistant stops archiving local-document test pages (`doc://`); `scripts/library_report.py` lists junk, move-only with `--apply`. | `.env`, `knowledge.search(namespaces=...)`, `goal_graph`, `graph.py`, new script | S |
| 1 | **Relevance filter** | The entailment call also answers `on_topic` for the question (same call, no extra cost). Off-topic facts are dropped and counted ("dropped 31 off-topic facts"). | `deep_report` (ENTAIL prompt, `extract_facts`) | S |
| 2 | **Coverage check at plan approval** | New step after planning: for every sub-question, judge the top retrieved passages (llama, about 3 calls per question) and mark it *answered / thin / nothing*, with the best titles found. Shown on the approval card. The user picks **Collect for gaps only / for all / none**; the collector then searches only the uncovered questions. | `goal_graph` (`coverage` node, approve payload and decision), `collector.discover(questions=gaps)`, `/deep` approval card | M |
| 3 | **Sufficiency gate and honest sections** | A section is *supported* if its questions have at least 3 relevant facts from at least 2 documents. Unsupported sections are written by code: "The library does not contain enough evidence on X. Found: (up to 2 cited facts). To answer this, collect: (search terms)". If fewer than half the evidence sections are supported, the report is an **evidence-gap report**: the summary says so, and recommendations are replaced by "Gaps and next steps". An *Evidence status* table (section, facts, documents, status) sits at the top of every report. | `deep_report` (`write_all`, `assemble`), thresholds in config | M |
| 4 | **One recommendation, consistency, de-duplication** | Write the synthesis section first and extract its one-sentence recommendation; the summary must state exactly that. Compare the two (llama, yes/no); on a mismatch, rewrite the summary once, else add a warning to Limitations. Evidence sections may describe trade-offs but not recommend. Drop paragraphs that repeat an earlier one (word-overlap), and strip filler openers ("The goal of this section ..."). | `deep_report` | M |
| 5 | **No uncited numbers; claim labels** | Any sentence with a number, no `[E#]`, and a number not found in the evidence is flagged `[inference, not from sources]` (plans and cost estimates are inference by nature, and labelled so). Every sentence gets `[established]` (cited, 2+ documents), `[single source]` (1 document) or `[inference]`: computed from the citations, no model call. Toggle `CLAIM_LABELS`. | `deep_report` (post-pass) | M |
| 6 | **Deliverable-aware planning** | Read the goal's "deliverable format" list and make each item a section, in order. Items that can be built from evidence are built by code: *key papers/models/datasets* becomes a linked table from the sources (title, kind, link, best fact), *risks* from cited facts. Items that are synthesis (decision table, recipe, 30/60/90 plan) are written from the findings and labelled as such. Honour "executive summary max N lines". | `deep_report` (`make_plan` deliverables, builders) | L |
| 7 | **Dashboard** | Coverage on the approval card (per question: answered / thin / nothing, with the choice to collect for gaps); *Include archived pages* toggle; Evidence status and gap notes on the run page; the report's status table renders as a table. | `/deep`, `run-view.tsx` | M |
| 8 | **Re-run, compare, record** | Re-run the saved goal (`logs/saved-goals-2026-10-01.md`) with collecting for gaps. Compare with the original on: facts judged on-topic in a 30-fact sample, contradictions between sections, uncited numbers, deliverables present, sections marked gap. Add an out-of-coverage goal as a standing test (must give a gap report, no recommendation, no invented numbers). Record in `EVALS.md`; update README, DECISIONS, runbook. | tests, `EVALS.md` | M |

Order: 0, 1, 2 first (they stop the worst failures), then 3, 4, 5, then 6, then 7 alongside, then 8. Backend stages are tested
offline with fake models; the services are restarted after 2 and after 5 for a live check.

## Defaults I propose (tell me if you want others)
- Supported section: at least 3 relevant facts from at least 2 documents. Evidence-gap report when under 50% of evidence sections
  are supported.
- Claim labels on by default.
- `Sources/` excluded from deep research by default (collected pages go to `Library/`, so they count).
- Coverage check runs at every plan approval (costs about 1-2 minutes) and again after a plan revision.
- Writer `gemma4:e4b`; classification-style JSON calls on llama.

## Cost and risks
- More model calls: coverage about 30 (llama), consistency 3-4. The relevance check adds none (same call as entailment).
- One model swap per run (about 30 s). With 8 GB, never two models at once.
- The gate could be too strict and mark decent sections thin: thresholds are settings and the status table shows the counts, so
  it can be tuned from real runs.
- Labels add visual noise to long reports; the toggle exists for that.
- Not planned: detecting and presenting disagreement between sources (hard with these models; the single-source label is the
  honest substitute).

## Exit tests (what "done" means)
1. The out-of-coverage goal yields a short gap report and no recommendation.
2. On the original goal, after collecting for gaps: no section's text contradicts the summary's recommendation, no sentence
   carries an unlabelled number that is not in the evidence, and every item of the requested deliverable list appears.
3. A sample of 30 evidence facts: at least 80% judged on-topic by a human (you).
4. All offline tests pass; lint clean; services restarted and a live run completes.
