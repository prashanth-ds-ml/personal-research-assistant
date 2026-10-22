# Scripts

Tools for running and maintaining Research Desk. Run them from the repo folder with `uv run scripts/<name>.py`; they
load `.env` and the project's packages through `_common.py`. `--help` shows each script's options.

## Set up and run

| Script | What it does |
|---|---|
| `setup.py` | one-time setup: tools check, tested package versions, models, settings, dashboard build, setup check |
| `start.py` | start the backend and the dashboard together; Ctrl+C stops both |
| `doctor.py` | setup check: Ollama and models, reranker libraries, vault, GPU power limit, free memory, ports |
| `start-research-assistant.ps1` | Windows: start both servers in the background (logs in `logs/`) |
| `register-task.ps1` | Windows: register the start script to run at log-on |

## Library (the dashboard's Library page calls the first four)

| Script | What it does |
|---|---|
| `collect.py` | fetch papers (arXiv, Europe PMC) and pages you name into the library, then index them |
| `ingest_library.py` | index folders of documents into the library |
| `reindex.py` | rebuild the library index (e.g. after changing the embedding model) |
| `library_doc.py` | re-index or remove one document (removed files move to `<vault>/.removed`) |
| `library_report.py` | what is in the library, by folder and kind, and documents that probably should not be evidence |

## Research runs

| Script | What it does |
|---|---|
| `run_deep_report.py` | goal to report from the library only, without the dashboard (no clarify / approve / collect) |
| `show_run.py` | print a run's live state from the dashboard's API |
| `audit_run.py` | quality audit of a finished run from its trace: health, reranker, use of passages, claim support |

## Elsewhere

- `dev/`: development checks against live services: `try_discover.py` (collector discovery for one question),
  `walkthrough_deep.py` (the whole flow through the dashboard's API), `check_disconnect.py` (a run survives the browser
  leaving the page), `backfill_runs.py` (run records for older runs).
- The experiments behind the case study's numbers are in [`evals/scripts/`](../evals/README.md), next to their data.
