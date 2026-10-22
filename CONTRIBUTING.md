# Contributing

Thanks for looking. Research Desk is a small project with a few firm rules, mostly about evidence: a change should show
its effect, and the reports must stay checkable.

## Set up for development

```bash
git clone https://github.com/prashanth-ds-ml/research-desk
cd research-desk
uv run scripts/setup.py        # tested versions, models, settings, dashboard build
uv run scripts/start.py        # backend + dashboard
```

Details and troubleshooting: [docs/SETUP.md](docs/SETUP.md). Install with `uv sync --locked` and `npm ci`, not
`pip install` / `npm install`: the lock files hold the versions everything is tested with.

## Before you open a pull request

```bash
uv run ruff check src tests scripts evals    # lint
uv run pytest tests -q                       # ~400 offline tests: no Ollama, no network
cd dashboard && npx tsc --noEmit && npx eslint src && npm test && npm run build
```

CI runs the same on every push and pull request.

## Ground rules

- **Discuss larger changes first** (open an issue). Small fixes can go straight to a pull request.
- **Tests come with the change.** A bug fix gets a regression test; a new behaviour gets tests that run offline (fake
  model, fake search: see `tests/conftest.py`).
- **Every report sentence stays checkable.** Sentences cite a passage; numbers and model names must appear in the
  cited passage (checked in code). Don't add a step that rewrites sources before the writer sees them: that is how the
  project's worst bug happened ([case study](docs/CASE_STUDY.md)).
- **A new stage or model change must show its effect** on the retrieval set (`evals/`), the code checks or user
  feedback, or it is not added. Record results in [docs/EVALS.md](docs/EVALS.md), whatever they show.
- **Chunking is locked** (`knowledge.CHUNKER`). Changing it needs a full re-index (`scripts/reindex.py --rebuild`) and an
  entry in [docs/DECISIONS.md](docs/DECISIONS.md).
- **Library content is never deleted** by the app; removed documents move to `<vault>/.removed`.
- **Versions are pinned.** Upgrading a dependency is its own pull request, re-tested; update the
  [tested versions](docs/SETUP.md#tested-versions-use-these-for-the-smoothest-setup) table.
- **Keep it simple.** Prefer removing a step to adding a check around it.

## Where things are recorded

| When you... | Update |
|---|---|
| find or fix a bug | [docs/ERROR_LOG.md](docs/ERROR_LOG.md) (new E-number: what happened, root cause, fix, regression test) |
| make a non-obvious design choice | [docs/DECISIONS.md](docs/DECISIONS.md) (append-only) |
| measure something | [docs/EVALS.md](docs/EVALS.md) |
| finish a milestone | [docs/STATUS.md](docs/STATUS.md) and [docs/PROGRESS_LOG.md](docs/PROGRESS_LOG.md) |
| change what users see or do | [docs/USER_GUIDE.md](docs/USER_GUIDE.md) / [docs/SETUP.md](docs/SETUP.md), and [CHANGELOG.md](CHANGELOG.md) |

## Code layout

`src/research_assistant/` holds the backend (the research graph is `goal_graph.py`; retrieval in `knowledge.py` and
`rerank.py`; writing and checks in `deep_report.py` and `report_checks.py`; collecting in `collector.py`). The dashboard
is a Next.js app in `dashboard/`. See the [README](README.md#repository-layout).

By contributing you agree that your contribution is licensed under the [MIT License](LICENSE).
