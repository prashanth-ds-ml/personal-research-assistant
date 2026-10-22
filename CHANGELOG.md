# Changelog

Releases: <https://github.com/prashanth-ds-ml/research-desk/releases>. How each stage was built and measured:
[docs/PROGRESS_LOG.md](docs/PROGRESS_LOG.md).

## 0.3.3 (2026-10-22)

- Case study rewritten as a one-page story (the failure, the fix, measured results and limits); the stage-by-stage
  record moved to `docs/PROGRESS_LOG.md`.
- "93% of sentences" now says what it measures: they pass the automatic checks, which is not a human accuracy score.
- Docs restructured: engineering records under `docs/`, superseded plans merged into three archive files, indexes for
  `docs/`, `scripts/`, `evals/` and `examples/`.
- Repository layout: experiment and evaluation scripts moved to `evals/scripts/` (next to their data), development
  checks to `scripts/dev/`; `scripts/` now holds only the tools users run.
- `examples/`: a real example report (with its evidence appendix) and the sample documents (moved from `sample_docs/`;
  `DOCS_PATH` default is now `./examples/sample_docs`).
- One name: the Python package is `research-desk` (was `personal-research-assistant`); default LangSmith project
  `research-desk`. The import name `research_assistant` is unchanged.
- CONTRIBUTING.md, SECURITY.md, issue and pull request templates, README badges.

## 0.3.2 (2026-10-22)

- Two-command quick start: `uv run scripts/setup.py`, `uv run scripts/start.py`.
- The dashboard's library actions use the project's own `.venv`.

## 0.3.1 (2026-10-22)

- Versions pinned to the environment Research Desk was developed and used with (`uv.lock`), Python 3.12-3.13.
- "Tested versions" in the setup guide; routine dependency PRs off.

## 0.3.0 (2026-10-22)

First public release of scope v3: deep research from library passages with one local model (`qwen3.5:4b`), hybrid
search with a reranker, sentence checks in code, run trace and feedback in the dashboard. Setup and user guides, CI on
every push.

Before 0.3.0 the repository held v1 (a fork of `langchain-ai/local-deep-researcher` with an Obsidian vault and profile);
see the case study for what changed and why.
