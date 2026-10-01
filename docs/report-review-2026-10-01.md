# Review of a real report: "Building a Small Language Model with Strong Reasoning and Reliable Tool/Function Calling"

Report: `<vault>/Research/Research/2026-10-01-building-a-small-language-model-with-strong-reasoning-and-re.md`
(11 questions, 7 sections, 150 verified facts, 19 sources, 336 model calls, 4,345 words of body text).
Goal: a long structured prompt with 7 research areas, a required deliverable format and research standards.

## Verdict
The report is not usable. It reads like a research report but is mostly filler built on the wrong evidence, and it
contradicts itself. The pipeline's checks (verbatim quote, entailment) worked as designed: every quoted fact is real. What
they cannot do is tell whether the fact is *relevant*, whether the library *covers* the goal, or whether the text written
*on top of* the facts invents things. Those are the gaps.

## What went wrong (with evidence from the report)

| # | Problem | Evidence |
|---|---|---|
| 1 | **The library did not cover the goal, and nothing said so before the run.** | Library check: 0 mentions of Chinchilla, BFCL, tau-bench, catastrophic forgetting; 1 chunk each for tool calling, function calling and continued pretraining; 3 for scaling laws. Four of the seven areas (scaling laws, reasoning, tool calling, decision analysis) had almost nothing. The run was started without *Find and collect new sources*, so "Nothing was searched on the web". |
| 2 | **Irrelevant evidence is kept because it is true.** | "Landscape of 4B-8B models" is built from BERT-large (213M) and T5-large (770M) numbers, a RAG paper and GPT-3 data mixes. The "Reasoning" section cites a CRAG evaluator's 0.77B size and AutoGPT. Facts are extracted per question without checking they are about the question's subject. |
| 3 | **The recommendation contradicts itself.** | Executive summary: pretrain from scratch is "most viable". Decision section: "we recommend using Continued Pretraining (CPT)". Practical recommendations: pretrain from scratch again. The same section admits "the evidence is too thin to provide a clear recommendation". |
| 4 | **Invented numbers.** | "Pretraining from scratch: 100-200 GPU-hours, $10,000-$20,000", CPT 50-100 GPU-hours, fine-tuning 10-50 GPU-hours. None is cited and no source in the library supports it; the pretraining figure is off by orders of magnitude. Synthesis and summary sections are not held to "cite every claim". |
| 5 | **Filler and repetition.** | "The goal of this section is to explore...", "it is unclear how this applies to small LLMs and Indian languages" repeated, the same conclusion paragraph three times, the 30/60/90 plan written three times in different forms ("Month 1-2: investigate the landscape" is not a plan). |
| 6 | **The requested deliverables are missing.** | The prompt asked for a decision table per budget scenario, a step-by-step recipe, a key papers list with links, risks with mitigations. The report has topic sections only; the decision table is a generic 3-row advantages table; there is no per-budget recommendation and no paper list. |
| 7 | **Claim labels and disagreement handling absent.** | No [established] / [single source] / [inference] labels; no section shows where sources disagree. |
| 8 | **Source list is unusable.** | "01-sciencedirect-com", "20 verticals · 7 ready-to-deploy now", "22-hydradb-com": file-name-like titles, no links, no way to tell PDFs from web pages. (Fixed below.) |
| 9 | **The whole prompt is pasted as the report's goal line.** | The header block holds all 4,900 characters of the prompt. (Fixed below.) |
| 10 | **Library pollution.** | 84 of 100 documents are pages the quick assistant archived into `Sources/`, many junk (18 are `doc://` pages from local-document tests, such as "Incident Response Runbook"). They dilute retrieval and show up as "sources". |
| 11 | **Indexed provenance text.** | Collected files were indexed with their YAML front matter, which contains the question each was found for, so they keyword-matched that question. (Fixed below.) |

## Fixed in this change
- Sources are recorded as **PDF / paper / web page / other document** with their URL (previously `source_url` was empty for all
  100 documents). The report's Sources section is split into *Papers and PDFs*, *Web pages* and *Other documents*, each
  linked, with how many facts each supplied and how many the report cites. The Limitations line says how many of each were used.
- The review step before collecting lists **PDFs and papers** and **web pages** separately.
- The Runs page shows **Collected for this run** and **Used in the report**, each as two lists (PDFs and papers / web pages).
- Front matter is no longer indexed (the library was rebuilt: 100 documents re-chunked, kinds and URLs filled in).
- The report header shows a short version of the goal.

## Proposed improvements, in order of impact (not built yet)
1. **Coverage check before the run (small, biggest win).** At plan approval, search the library for each question and show
   "answered / thin / nothing" per question, and offer to collect sources for the thin ones. Would have said, before an hour of
   work, "your library has nothing on scaling laws, tool calling or forgetting".
2. **Relevance filter on facts.** One cheap model call per fact ("is this about <question subject>?"), or a retrieval score
   floor, so BERT-large numbers never reach "4B-8B landscape".
3. **Evidence-sufficiency gate and an honest mode.** If a section has too few relevant facts, write a short "what the library lacks
   and what to collect" section instead of filler; if the overall evidence is thin the executive summary must say "not enough
   evidence to recommend", and the recommendation section becomes "gaps and next steps".
4. **One recommendation, stated once.** Write the decision section first, extract its recommendation, and make the summary and
   practical sections quote it; a consistency check compares the recommendation across sections and rewrites on a mismatch.
5. **No uncited numbers in synthesis.** Numbers in summary/synthesis text must appear in the cited evidence; otherwise they are
   removed or marked "[inference, not from sources]". Add the claim labels ([established] / [single source] / [inference]).
6. **Deliverable-aware planning.** Read the goal's "deliverable format" and make each item a section (decision table,
   recipe, key papers with links, risks, plan), written from evidence, with tables built from facts and marked synthesis where not.
7. **De-duplication across sections** so the same conclusion is not written three times.
8. **Library hygiene.** Keep curated sources (`Library/`) separate from archived quick-research pages (`Sources/`): exclude
   `Sources/` from deep research by default or rank it lower, and stop archiving local-document test pages.
9. **Writer model.** The writer and synthesis steps use a small local model; trying a larger or different one for synthesis only
   (the benchmark in BENCHMARKS.md found gemma4:e4b writes better than llama3.1:8b) is cheap to test.

Items 1-3 address most of what made this report misleading; 4-5 address the self-contradiction and the invented numbers.
