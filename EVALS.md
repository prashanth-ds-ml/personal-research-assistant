# Reliability check + demo script

## Reliability check: does personalization actually change behavior?

The core claim of this project isn't "it can search the web" (the stock
tutorial already does that) - it's "it gets better at helping *you*
specifically the more you use it." That's the thing worth verifying, since
it's easy to build the plumbing (profile note, vault retrieval) without it
actually affecting anything.

**Test**: run two related topics back-to-back and check three things.

1. **Source archive populates.** After a run, `Sources/<date>-<topic>/`
   should contain one markdown file per source with real frontmatter
   (`url`, `title`, `query`, `fetched_at`) and either the full page content
   or a binary-source stub. (Verified 2026-09-28: confirmed via a direct
   unit test of `vault.archive_sources` with both a normal HTML source and a
   `.pdf`-extension source - the PDF correctly got stubbed instead of
   mangled.)
2. **Vault-as-context surfaces prior work.** Ask about a topic adjacent to
   an existing note (e.g. "context engineering and RAG" after already having
   a RAG report) and confirm the retrieved context names the right prior
   note. (Verified 2026-09-28: asking about "context engineering" correctly
   surfaced the earlier "What is retrieval augmented generation?" report as
   the top match, with the right title and filename.)
3. **Profile evolves and is append-only.** After a run, `Profile.md`'s
   `## Session Log` should have a new dated entry, and `## Standing
   Preferences` should be byte-for-byte unchanged. (Verified 2026-09-28: ran
   a full "What is MCP?" research session - the Session Log gained a dated
   entry with real bullets about the session's topic and jargon, and the
   Standing Preferences section was untouched.)

**Automated**: all three checks above (plus report-link resolution and
filename-collision handling) now run as `pytest tests/` - offline, no Ollama
or network needed (retrieval uses a deterministic fake embedding model, so it
verifies the plumbing, not embedding quality). Run it after any change to
`vault.py`. The live-model behavior below (does a third run actually *use* the
profile?) still needs the manual check.

**What "good" looks like**: a third run on a related topic should visibly
reference the first two (either in the generated search query or the
summary's phrasing), and its profile-update entry should build on, not
repeat, the earlier ones. What would indicate a real problem: the profile
entries becoming generic/repetitive regardless of topic (prompt not
actually using the profile), or vault context always coming back empty even
when clearly-related prior notes exist (retrieval broken).

**Known limitation**: even with `ddgs` (see `DECISIONS.md`), the underlying
free HTML-scraping search backend can occasionally rate-limit and return
zero sources for a run. The pipeline degrades gracefully (a report with no
archived sources for that run, not a crash) rather than failing outright -
not something to chase further without switching to a paid search API.

## Demo script (~2 minutes)

1. **Open the dashboard** (`http://localhost:3001`) - show the history page
   with a couple of existing reports. *"This reads straight from my
   Obsidian vault, not from some database - the vault is the actual
   history."*
2. **Click into a report** - show the `## Key Findings` / `## Open
   Questions` / `## Sources` structure, click a source link to show it
   opens the full archived page content, not just a URL.
3. **Open `Profile.md`** in the dashboard's Profile tab - point at the
   `## Session Log` entries. *"Every time I research something, it writes
   itself a note about what I'm interested in - and I can edit `Standing
   Preferences` myself, it never touches that part."*
4. **Start a new research topic** related to an existing note (e.g. if you
   have a report on RAG, ask about "vector databases for RAG"). Watch the
   live status update (current query, loop count) as it streams.
5. **When it finishes**: point out the Windows toast notification, click it
   to jump straight to the new report - then open the report and show it
   explicitly references or builds on the earlier RAG note, instead of
   starting from scratch.
6. **Try a comparison** (e.g. "Compare PostgreSQL vs MongoDB vs Redis for
   analytics workloads"). *"It detected this is a comparison and
   researched all three in parallel - not sequentially - then wrote one
   report comparing them."*
7. **Open the Knowledge Graph tab** - show the notes clustering by topic
   similarity. *"This is the same retrieval it uses to build on prior
   research, just visualized."*
8. **Close with the "why"**: *"Same iterative research loop as the open-
   source tutorial this is forked from, but instead of a one-off answer, it
   builds a permanent, linked, personalized knowledge base - compares things
   in parallel instead of one at a time, and
   starts automatically when I log in, so it's just always there."*

---

# Deep research mode: evals

The goal-driven pipeline (`deep_research` graph: clarify -> plan -> approve ->
extract -> write) is measured, not just demoed. Everything below is reproducible
from `evals/` and `scripts/` against the 11-paper library in `library/`.

## 1. Retrieval: does hybrid search earn its complexity?

`python scripts/eval_retrieval.py` - 25 questions, each with the paper that
answers it and a phrase that must appear in the retrieved chunk (a chunk from
the right paper that does not contain the answer does not count). Answer
phrases were validated to exist in the expected paper.

| method | recall@1 | recall@3 | recall@6 |
|---|---|---|---|
| BM25 (FTS5) | 68% | 80% | 92% |
| dense (qwen3-embedding:0.6b) | 48% | 72% | 92% |
| **hybrid (reciprocal-rank fusion)** | **80%** | **92%** | **96%** |

Hybrid wins at every cutoff; the two methods fail on different questions
(keywords catch exact terms like "Leiden" or "28.4"; embeddings catch
paraphrase), which is the whole argument for fusing them. These numbers are
after removing reference/acknowledgement chunks (139 of 959); that cleanup left
hybrid unchanged and moved dense recall@3 from 68% to 72%.

## 2. Report quality across pipeline changes

One fixed goal, `llama3.1:8b` in every role, same library. Each row is the
pipeline after one fix, so the table is an ablation of the fixes themselves.
(Counts are from the finished markdown; "cited facts" = distinct evidence ids
cited in the body. Read it as *volume*, not quality: v1 cites the most facts
precisely because nothing filtered out the wrong ones. The quality signals are
which papers are used, whether sections answer their question, and, once
labelled, the faithfulness numbers in section 3.)

| version | change | body words | cited facts | papers used | notes |
|---|---|---|---|---|---|
| v1 | first slice, no faithfulness check | 1,455 | 64 | 9/11 | planner invented a false premise; GPT-3 numbers labelled "local models" - more facts, but some misattributed |
| v2 | goal-faithful planner, subject-naming claims, judge, dedupe | 2,003 | 45 | 6/11 | premise fixed, misattributions filtered (fewer but truer facts); "learn from examples" section still wrong |
| v3 | multi-query retrieval, per-paper cap, titles | 1,995 | 54 | 10/11 | right papers now retrieved |
| v4 | HyDE query, drop reference chunks, retries | 1,689 | 54 | 11/11 | one empty section (recommendations cannot be retrieved) |
| **v5** | **synthesis section written from other sections' findings** | **2,165** | **57** | 8/11 | recommendations section grounded; no empty sections |
| v5 + gemma writer | llama plans/extracts, gemma4:e4b writes | 2,619 | 57 | 9/11 | longer, better-organised prose; ~8% slower |
| v6 (after audit fixes) + gemma writer | same mix; re-chunked library, evidence merged across questions, hardened pipeline | 2,498 | 66 | 12 docs | 0 empty sections, 0 retries; 12 sources vs 9 in v5; thinner failure-modes section (249 words) |

Each run makes about 165 model calls and takes 11-12 minutes on an RTX 5050
(8 GB). The retry wrapper recorded 0 retries in v4/v5; the failure that
motivated it (Ollama "token repeat limit reached", which killed one run) did
not recur.

## 3. Faithfulness: is the automatic claim check trustworthy?

Every claim is checked twice: its quote must appear verbatim in the passage
(deterministic), and a second model call must judge that the passage supports
the claim - including that the claim is about the right subject. The judge
catches the failure that motivated it (a benchmark number attributed to
"local models" when the passage says GPT-3), but "the judge works on one
example" is not evidence.

To measure it properly:
```bash
python scripts/make_faithfulness_sheet.py --n 50   # 25 accepted + 25 rejected claims
# open evals/faithfulness_sheet.csv, fill `human` with y/n (claim fully supported by the passage), ~10 minutes
python scripts/score_faithfulness.py evals/faithfulness_sheet.csv
```
It reports the judge's two error types separately: **false accepts** (an
unsupported claim gets into the report - the dangerous one) and **false
rejects** (good evidence is thrown away). Sampling both accepted and rejected
claims is what makes the second number measurable.

**Status: PRELIMINARY, labelled by Claude, not yet by a human.** The 50 claims were
labelled as a first pass by the assistant (column `claude`; the `human` column is for your
verification, starting with the rows marked `borderline`). Treat everything below as
provisional until a human has confirmed the labels.

Scored against those labels (`python scripts/score_faithfulness.py evals/faithfulness_sheet.csv claude`;
`python scripts/rejudge_sheet.py --model <m> --labels claude`). The sample is stratified
(25 judge-accepted + 25 judge-rejected claims), so accuracy is *not* the population
accuracy; the two error counts are what matter.

| judge model | accuracy | false accepts (unsupported claim kept) | false rejects (good claim dropped) | recall of supported |
|---|---|---|---|---|
| llama3.1:8b, as recorded in the sheet | 88% | 0 of 25 accepted | 6 | 81% |
| llama3.1:8b, re-run | 90% | 0 of 26 accepted | 5 | 84% |
| gemma4:e4b | 96% | 1 of 31 accepted | 1 | 97% |

What this says, with the caveats that n is small and labels are provisional:
- **No unsupported claim got past the llama judge** in this sample (0 of 25-26). With
  only ~25 accepted claims, that is consistent with a true false-accept rate anywhere up
  to about 12% (rule of three), so it is encouraging, not proof. The plan's rule (try a
  different judge if more than 10% of accepted claims are unsupported) is **not
  triggered**; llama stays the default judge.
- **The llama judge is too strict, not too loose:** it dropped 5-6 of 31 genuinely
  supported claims (about 1 in 5). Three of those were numbers read from a markdown table
  (the model struggles to line a value up with its column header); three were claims the
  passage supports but the extractor's chosen quote did not. That wastes evidence; it
  does not add errors.
- **Gemma judges better on this sheet** (recall 97%, 1 false reject) but accepted one
  wrong claim (it took the three RAG *components* for the three *paradigms*). Trading 5
  fewer false rejects for 1 false accept may be worth it, but that is a call to make on
  human-verified labels, not these. Not changed yet.
- **Not deterministic:** the same llama judge flipped one of 50 verdicts between runs at
  temperature 0, so differences of one or two claims are noise.
- **The extractor is the weaker link:** 19 of the 50 raw claims were unsupported (38%),
  mostly wrong-subject errors ("GPT-3 has 406M parameters", taken from a passage about the
  RAG model). The judge removes nearly all of them, which is the point of having it.

## 4. Known failures (not fixed)
- **Composite misreads pass the checks.** v5 recommendations say a
  "combination" of chain-of-thought and fine-tuning "achieved state-of-the-art
  on math word problems"; each half is in the evidence, the combination is not.
  Verbatim + per-claim checks cannot catch a synthesis error across claims.
- **Recommendations are generic.** The 8B writer produces sound but
  undifferentiated advice; a better synthesis model is the obvious next test.
- **Planner variance.** Same goal, same model, different runs produce 5-7
  sections and different question splits (the planner runs at temperature 0, so differences come from the model and the evidence, not sampling).
- **Thin evidence for "learn from examples".** The few-shot paper is in the
  library but that section still leans on general RAG passages; retrieval is
  better (recall@6 96%) but not perfect (one miss: the chain-of-thought
  definition).

## 5. Retrieval with distractors (library grown from 11 to 77 documents)

Same 25 questions, same paper-level answers; 66 archived web pages from the vault
added as distractors.

| method | recall@1 | recall@3 | recall@6 |
|---|---|---|---|
| BM25 | 68% | 80% | 88% |
| dense | 48% | 68% | 92% |
| **hybrid** | **76%** | **88%** | **96%** |

Hybrid still wins at every cutoff and keeps recall@6 at 96%. Top-rank precision
drops a few points as the library grows, which is why the pipeline retrieves 6-8
passages per question instead of trusting the first hit.

## Live run with web collecting (2026-10-01)
Goal: "What do practitioners recommend for chunking documents in RAG systems?" with *Find and collect new sources first*.
Discovery found 40 candidates in about 150 s (web pages and papers from arXiv and Europe PMC); 3 were chosen, 1 returned HTTP 403
and was skipped, 2 papers were saved and indexed; research then used the library of 100 documents. Result: 7 questions, 6
sections, 45 verified facts, 3,241 words, 5 distinct sources cited, 1 section without evidence, 0 model retries, 123 model
calls, about 13 minutes in total. One run, one goal: it shows the pipeline works end to end, not that web pages improve
reports. The candidate list included low-quality sites (forums, social posts), which is why the review step and
`COLLECT_ALLOW_DOMAINS` exist.

## Report-quality changes: what was and was not validated (2026-10-01, evening)
- **Validated:** the coverage check on an out-of-coverage goal (all 7 questions "nothing", confirmed by a direct library search) and on
  the small-model goal (12 questions: 1 answered, 7 thin, 4 nothing, matching why the original report was poor). 285 offline tests cover
  the gate, labels, consistency check, failed-section handling and the collector.
- **Not validated:** the evidence gate, claim labels and consistency check on a healthy end-to-end run. The one full run (chunking goal,
  about 2.5 hours) was disturbed by a power-capped GPU: all four sections failed to write, which exposed and led to fixing a bug (see
  DECISIONS), so it shows the failure handling, not report quality. Label accuracy, the 30-fact on-topic sample and the contradiction
  check on a real report are still to measure.
- **Not done:** deliverable-aware planning (the requested decision table, recipe and paper list as sections).

# Phase 1a-0: Measure first (from 2026-10-19)

Plan: `docs/phases/phase-1a0-measure-first.md`. Tooling: `src/research_assistant/eval_tools.py` (tests in
`tests/test_eval_tools.py`), `scripts/error_analysis.py`, `scripts/build_subject_eval.py`, `scripts/judge_calibration.py`.

## Eval assets

| Asset | What | Status (2026-10-19) |
|---|---|---|
| `evals/error_analysis/claims.csv` + `claims.md` | 50 claims sampled (seed 1, stratified) from the 10-02 and 10-03 reports (pool: 193 cited claims), each with its facts, quotes and library passages | Built. Claude labelled blind (`claude_labels.csv`); human labels pending (U-02). Breakdown published after both |
| `evals/subject_facts.jsonl` | 42 extraction cases: passage + question + expected system / size / stage (+ modality / task), incl. E7, E8, E79, E76, E40 | Built (labels by Claude; spot-check in U-02) |
| `evals/faithfulness_human.csv` | Blind copy of 20 faithfulness rows (8 disputed + 12 random) for judge calibration | Built; human labels pending (U-P2) |
| `evals/kb/retrieval_v1.sqlite` | Frozen index of the 11-paper retrieval corpus (`ObsidianVaults/eval-corpus/retrieval-v1`, copied from the 10-02 archive), separate from the live library | Built 2026-10-19: 11 documents, 889 chunks, 606 s |
| Held-out goal (E-010) | A gold goal the prompts were never tuned on | User to choose (U-P5) |

## Baselines so far

- **Retrieval on the frozen corpus (25 questions, `evals/results_retrieval_2026-10-19.json`):**

  | method | recall@1 | recall@3 | recall@6 | 2026-09-30 (same questions) |
  |---|---|---|---|---|
  | bm25 | 68% | 84% | 92% | 68 / 80 / 92 |
  | dense | 52% | 68% | 88% | 48 / 72 / 92 |
  | hybrid | **80%** | **88%** | **96%** | 80 / 92 / 96 |

  Reproduces the September result within one question per cell (chunking changed since: 889 chunks now). Retrieval
  over a known corpus is not the bottleneck; whether the *right documents get collected* is a separate question
  (see "bad source" in the error analysis).
- **v1 extraction subject accuracy on the subject set: 22/42 (52%).** The set is deliberately rich in traps (the
  E-001 family), so this is a baseline to beat on the same set, not an estimate for all facts.
- **Judge calibration: not computable yet.** The first version of the script reported 100% agreement, which was
  circular: with no human labels, the reference was "where the judge and Claude agree". Fixed: the decision number
  is now agreement with human labels only (blind copy); the mixed reference is printed as an upper bound.
- **Claim-level error analysis: pending U-02.** Method notes: labels are blind per labeller; a new stage
  `writing subject` was added while labelling (fact right, report sentence drops or changes its subject), because
  several failures did not fit `extraction subject` or `writing stitch`. Claim-level analysis cannot see
  retrieval misses (they show up as gaps, not cited claims); those are counted from the reports' evidence-status
  tables.
- **Scope of the sample:** both reports predate the October fixes (goal-aware judging, plans kept on the goal), so
  this measures the pipeline before those fixes. The Sprint 4 re-run measures it after.

## v3 M1: report from passages, one model (2026-10-19)

Same goal and library as the 2026-10-03 v2 report that showed E-001 ("How to pretrain a 4B model from scratch for Telugu,
English and transliteration, good at reasoning and native tool calling"; 114 documents). `scripts/run_deep_report.py`
(library only, no collecting), `qwen3.5:4b`, thinking off, 16k context. Report and log: `evals/v3/m1-pretrain-4b.*`.

| | v2 (2026-10-03, facts, llama3.1:8b + gemma4:e4b) | v3.0 (passages, qwen3.5:4b) |
|---|---|---|
| Time | hours (multi-model, extraction per passage) | **229 s**, 72 model calls, 0 failures |
| Body words (summary → last section) | ~4,000 | **1,289** |
| Evidence items | 42 extracted facts | 16 passages (32 retrieved passages judged not useful) |
| E-001-type claims (wrong subject stated as fact) | several (E7/E8, E79, E76...) | **none found on reading**; sections name the real subject ("a full fine-tune of Qwen3-4B-Instruct", "pertains to a different scale") |
| Code-check flags | n/a | 1 subject flag that is a false positive (a sentence saying a source does *not* cover a 4B model); a second false positive (Qwen3-4B-Instruct vs "Inst.") fixed |
| Outcome | full report with a recommendation | **gap report**: 2 of 5 sections supported, no recommendation; says which sources to collect |

Reading: v3 is honest where v2 was confident. The library really lacks Telugu pretraining-data and compute sources; v2 filled
that gap with fine-tune and 17B-model numbers re-labelled as 4B pretraining. The real flow adds web collecting for the
uncovered questions, which this script skips.

Found and fixed on the way: E-014 (thinking mode emptied the plan), E-015 (yes/no relevance rejected nearly every passage →
0-3 grade, keep 2+), gap notes now quote the passage start, section bar 2 passages from 2 documents.
Known limits: the subject check cannot read negation ("does not cover a 4B model" is flagged); the status table still says
"Facts" for passages.

## v3 Test A: chunk size (2026-10-19)

Frozen retrieval corpus (11 PDFs) re-chunked at each size, 25 questions, the pipeline's hybrid search
(`scripts/exp_chunk_size.py`, raw: `evals/v3/exp_a_chunk_size.json`). A hit needs the right document and an answer phrase.
"Within N chars" = the top chunks that fit in N characters of reading: equal cost for every size.

| Max chunk chars | Chunks | Avg chars | Top 1 / 3 / 6 | Within 2k / 4k / 8k chars |
|---|---|---|---|---|
| 600 | 1,996 | 688 | 64 / 88 / 92% | 88 / 92 / 100% |
| 1,000 | 1,431 | 923 | 64 / 84 / 96% | 80 / 84 / 96% |
| 1,400 | 1,184 | 1,096 | 80 / 84 / 96% | 80 / 92 / 96% |
| **1,800 (kept)** | 979 | 1,256 | **80 / 88 / 96%** | 84 / 88 / 96% |
| 2,500 | 801 | 1,457 | 80 / 92 / 92% | 80 / 92 / 92% |
| 3,500 | 685 | 1,636 | 76 / 96 / 96% | 76 / 92 / 96% |

One question = 4 points, so most differences are noise; small chunks are clearly worse at ranking the right chunk first.
Decision: keep 1,800 and lock it (DECISIONS "Chunk size locked"). After the lock and re-chunk the frozen check is unchanged.

## v3 report review: the first real report (2026-10-19)

*Embedding Models: Architecture, Training Data, and Pipeline Construction* (run 01a154bc, 22 min incl. collecting 51 sources;
17 of 24 passages kept; 136 model calls, 0 failures; 45 sentences: 42 clean, 1 figure flag, 1 subject flag, 1 uncited).
Read against its chunks: claims mostly exact; problems found: citation drift between neighbouring chunks of one paper
(word coverage 0.08 on the cited chunk vs 0.75 on the right one), an uncited table from another context, a stitched
model-written summary, flags placed on the next sentence, errors copied from a source (IBM: "encoder-decoder ... BERT"),
and thin coverage of "which datasets" (only CCPairs). Fixes: see DECISIONS "Report checks tightened".

## v3 Tests B and C: harness ready, not run (2026-10-19)
`scripts/exp_context.py`: fixed graded passage pool for 4 questions (11/12/7/14 passages scored 2+), shuffled positions,
exact token counts from Ollama, 32k window; C varies passages per section 4/8/12/16/24, B neighbour expansion on/off,
`think` repeats the best size with thinking. The pool must be rebuilt first (library re-chunked after it was built).
