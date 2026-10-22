# Examples

## An example report

[report-local-private-rag.md](report-local-private-rag.md) is a real, unedited report (the final test run in the
[case study](../docs/CASE_STUDY.md)), written by `qwen3.5:4b` on a laptop in 17 minutes:

> *Building a private RAG system for a small team: which embedding models to use, how to chunk documents, hybrid keyword
> and vector search, reranking, how to evaluate retrieval and answer quality, and how to run the whole system locally on
> a single 8 GB GPU.*

What to look at:

- **Evidence status** at the top: how many passages and documents stand behind each section; one section is marked
  *thin* and says what is missing instead of guessing.
- **Citations** like `[E3]` after every sentence. Each points to a passage quoted in full in the **Evidence appendix** at
  the end, with its document and section.
- **Flags** such as `[cited; domain ...]` on sentences that failed an automatic check (here: a medical study cited
  without naming its domain).
- **Sources**: the 18 documents used (papers, official docs, web pages), with links.

In the dashboard the same report shows each passage next to its sentence, with buttons to rate it (see the
[user guide](../docs/USER_GUIDE.md#read-a-report)). The only change from the original file: `~` is written as `\~` so
GitHub does not show it as crossed-out text.

## Sample documents

[sample_docs/](sample_docs/) holds two small made-up company documents (an employee handbook PDF and an incident
runbook) for trying the quick assistant's *Internal documents* search (`DOCS_PATH` in `.env`). For deep research, put
your own files in `<vault>/Library` instead.
