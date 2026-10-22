# Evaluation: data, results and the scripts that produced them

The evidence behind the numbers in the [case study](../docs/CASE_STUDY.md); the full write-up of every run is in
[docs/EVALS.md](../docs/EVALS.md). Run a script from the repo folder: `uv run evals/scripts/<name>.py --help`.

## Experiments (v3)

| Script | What it measured | Result files |
|---|---|---|
| `scripts/eval_retrieval.py` | keyword vs vector vs hybrid search on the frozen question set | `results_retrieval_2026-10-19.json` (hybrid top 1/3/6: 80/88/96%) |
| `scripts/exp_chunk_size.py` | Test A: which chunk size retrieves best (chose 1,800 characters) | `v3/exp_a_chunk_size.json` |
| `scripts/exp_context.py` | Tests B, C, D: passages and words per section a 4B model handles (about 8 passages, about 600 words) | `v3/exp_context.jsonl`, `v3/exp_pool.json` |
| `scripts/exp_rerank.py` | does the reranker put the answering passage higher (top 3: 88% to 100%) | `v3/exp_rerank.json` |
| `../scripts/audit_run.py` | audits of four real runs; `audit_01a158a7.json` is the final test report | `v3/audit_*.json` |
| `../scripts/run_deep_report.py` | the v3 report on the E-001 question (same goal and library as the report that showed the error) | `v3/m1-pretrain-4b.md` |

## Data

| File | What it is |
|---|---|
| `retrieval_qa.json` | the frozen retrieval set: 25 questions, each with the document and phrases that answer it |
| `results_retrieval.json`, `results_retrieval_77docs.json` | earlier retrieval runs (11 and 77 documents in the library) |
| `kb/` | the frozen retrieval index; rebuilt locally by `scripts/ingest_library.py`, not in git |

## Earlier work (v2 and v1)

- v2 claim labelling, judge calibration and error analysis (the work that led to scope v3): `scripts/error_analysis.py`,
  `build_subject_eval.py`, `make_faithfulness_sheet.py`, `judge_calibration.py`, `rejudge_sheet.py`,
  `score_faithfulness.py`; data in `faithfulness_sheet.csv`, `faithfulness_human.csv`, `subject_facts.jsonl`,
  `error_analysis/`.
- v1 model choice (chat speed, parallel tool-calling reliability): `scripts/benchmarks/`; results in the
  [v1 archive](../docs/archive/v1-2026-09-29-to-10-03.md).
