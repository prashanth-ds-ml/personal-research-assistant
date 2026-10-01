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
