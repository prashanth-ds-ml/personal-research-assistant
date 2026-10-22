# Evaluation data and results

The data behind the numbers in the [case study](../docs/CASE_STUDY.md) and [EVALS.md](../docs/EVALS.md). Scripts that
produce them are listed in [scripts/README.md](../scripts/README.md).

| File | What it is |
|---|---|
| `retrieval_qa.json` | the frozen retrieval set: 25 questions, each with the document and phrases that answer it |
| `results_retrieval_2026-10-19.json` | keyword vs vector vs hybrid on that set (hybrid top 1/3/6: 80/88/96%) |
| `results_retrieval.json`, `results_retrieval_77docs.json` | earlier retrieval runs (11 and 77 documents in the library) |
| `v3/exp_a_chunk_size.json` | Test A: retrieval at six chunk sizes (chose 1,800 characters) |
| `v3/exp_context.jsonl`, `v3/exp_pool.json` | Tests B, C, D: passages and words per section the 4B model handles (about 8 passages, about 600 words) |
| `v3/exp_rerank.json` | reranker on the frozen set (top 3: 88% to 100%) |
| `v3/audit_*.json` | audits of four real runs (`scripts/audit_run.py`); `audit_01a158a7.json` is the final test report |
| `v3/m1-pretrain-4b.md` | the v3 report on the E-001 question (same goal and library as the report that showed the error) |
| `faithfulness_sheet.csv`, `faithfulness_human.csv`, `subject_facts.jsonl`, `error_analysis/` | v2 era: claim labelling, judge calibration and error analysis that led to scope v3 |

`kb/` (the frozen retrieval index) is rebuilt locally by `scripts/ingest_library.py` and is not in git.
