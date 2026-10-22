# Case study: a research assistant that shows its work

**Research Desk** · local deep research on one laptop · built Sep-Oct 2026 · [repo](../README.md) ·
[detailed progress log](PROGRESS_LOG.md)

## In 60 seconds

AI research agents write fluent reports. Read closely, some claims are wrong in a way that is hard to catch: **the quote
is real, but it is about a different model, size or stage than the sentence claims.** Research Desk was built to make
that kind of error rare and, when it happens, easy to spot. It runs on one laptop (8 GB GPU, Ollama, one 4B model, no
cloud) and writes reports in which every sentence cites the passage it came from, checked in code.

The project's turning point was a report that passed all its own checks and was still wrong. The fix was to **remove**
a pipeline step, not to add checks around it. On the same question, the new version wrote less but stayed on the real
subject, and said plainly where the evidence ran out.

## The problem

A team deciding something real needs research it can trust. Two constraints were chosen on purpose:

- **Private:** everything runs locally, no paid APIs, documents never leave the machine.
- **Ordinary hardware:** a laptop with an 8 GB GPU and 24 GB RAM, so a small model (4B parameters) has to do the work.

## The failure that shaped it

An earlier version answered *"How to pretrain a 4B model from scratch for Telugu, English and transliteration"* from a
library of 114 documents. The report read well, every quote was verbatim, and every automatic check passed. Reading it
against its sources:

| The report said | The source actually was |
|---|---|
| "Optimal hyperparameters for **pretraining** a 4B model from scratch" | a paper about **post-training** (fine-tuning) |
| "**Pretraining a 4B** model ... 22.63T tokens" | the model card of a **17B** model |
| A summary sentence combining numbers from four sources, labelled *established* | four different models and setups |

On a closer count, only **22 of 42** extracted facts kept the right subject.

**Why:** a step rewrote each source passage into a short "fact" phrased in the *question's* terms, so "a 17B model was
trained on 22.63T tokens" became a fact about pretraining a 4B model. The checks then confirmed the quote existed, never
that it was about the same thing.

**The fix:** delete the rewriting step. The writer now reads the source passages themselves, each labelled with its
document title and section, and code checks every sentence: numbers and model names must appear in the passage it
cites. Same question, same library, new version:

> "...while the Qwen3-32B model showed high accuracy (88.6±.7) with tool calling, this result pertains to a different
> scale and language context than the proposed 4B multilingual system [E14]."

It finished in 4 minutes instead of hours, supported 2 of 5 sections, gave **no recommendation**, and listed which
sources to collect. Less impressive, and correct: the library really had no Telugu pretraining sources.

**Lesson:** a check must test meaning, not only form. "Is the quote real?" is not the question; "is it about the same
thing?" is.

## How it works now

```
goal -> clarifying questions -> plan (you approve) -> collect sources (you pick) -> library
library: chunks + keyword search + vectors -> reranker -> best 8 passages per sub-question
write one section per sub-question from its own passages, every sentence cited
code checks every sentence (numbers, model names, word overlap, domain) -> flags in the report
you rate passages and flag sentences in the dashboard -> stored with the engine version
```

![A report chapter: each sentence cites a passage, shown in the margin with feedback buttons](images/report-chapter.png)

## Results

Final test report (*Local private RAG system design for small teams*, run 01a158a7):

| | |
|---|---|
| Time | 17 minutes on the laptop |
| Sections | 5 of 6 written; the 6th stated as a gap (no source on embedding-model memory use) |
| Length and sources | 2,979 words from 18 documents (5 papers, 3 official docs, 10 web pages) |
| Sentences passing the automatic checks | 144 of 155 (93%); 8 had no citation, 3 were flagged for not naming a source's domain |

**What "passing the automatic checks" means:** the sentence cites a real passage, its numbers and model names appear in
that passage, and enough of its words do. **It is not a human-verified accuracy score:** the checks cannot catch a source
that is itself wrong, or a conclusion that does not follow from correct facts. In one audited run, 79% of cited sentences
had at least 70% of their words in the passage they cite, and spot-checked numbers were verbatim.

What was measured along the way:

| Question | Answer | How it was measured |
|---|---|---|
| Does the reranker help? | Clearly offline (right passage in the top 3: 88% to 100%), small and mixed on real runs (32 vs 28, then 25 vs 27 useful passages) | 25-question retrieval set; two audited runs |
| How many passages can a 4B model use per section? | About 8; beyond that it drops sources, the late ones first | 48 measured section writes |
| How long can a section be? | About 600 words; past ~800, a quarter of sentences had no source (the model pads) | 48 measured section writes |
| Is "thinking" worth it? | Yes: clean sentences 77% to 92%, for about 7 extra minutes | same goal run with and without |
| Memory | 11-12 GB free RAM per run | measured on Windows |

**Scope of this evidence:** one user, AI/ML research questions in English, and most numbers come from repeated runs on
two goals. Other domains and languages are not measured yet.

## Decisions and trade-offs

| Chose | Over | Because |
|---|---|---|
| Write from the source passages | Extract facts first, then write | The rewriting step was where subjects got lost (22 of 42 right) |
| One 4B model for everything | A planner, an extractor and a writer | Fits an 8 GB GPU with no model swapping; quality held once extraction was gone |
| Checks in code | A second LLM as judge | Code is predictable; an early LLM judge rejected everything because of its own prompt rules |
| Fewer, shorter, cited sections | Long reports | Measured: accuracy holds to ~600 words per section, then the model pads |
| Daily use and feedback as the evaluation | A 50-claim labelling project | The plan had grown to 12 sprints; simplifying got the tool into use |
| Pinned, tested versions | Always the latest packages | Reproducible setup for people who clone it |

## Lessons

1. **Test meaning, not form.** A real quote can still support a false sentence.
2. **When complexity causes errors, remove a step before adding a check.**
3. **Retrieval failures look like writing failures.** Read what was retrieved before rewriting prompts.
4. **Check the machine before blaming the model.** A 5-10x slowdown was a power-capped GPU (10 W), not the model.
5. **Measure your own limits.** The usable context of a 4B model was set by section length and position, not the
   context window.
6. **Watch for process outgrowing the product.** The plan grew to 12 sprints before anything new was usable; cutting it
   back put the tool into daily use.
7. **"Works on my machine" is literal.** Releasing it, a fresh clone found a page never committed to git, a lock file
   that had drifted from the real environment, and a Python version that could not install.

## What's next

- **Real-use numbers:** source ratings and "was this report useful" from daily use, stored per engine version, to give
  before/after evidence the automatic checks cannot.
- **A comparison run:** the same question through the original
  [local-deep-researcher](https://github.com/langchain-ai/local-deep-researcher) and through Research Desk, side by side.
- **Chat over the library** (same retrieval and checks).

Details: [progress log](PROGRESS_LOG.md) (every stage and measurement) · [EVALS.md](EVALS.md) (raw results) ·
[DECISIONS.md](DECISIONS.md) · [ERROR_LOG.md](ERROR_LOG.md) (every bug, E-numbers).
