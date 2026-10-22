# Research Desk

Local deep research that builds your own private library. You give it a goal; it plans sub-questions, collects web
pages and papers, indexes them, and writes a short report in which **every sentence cites a source passage**. Everything
runs on your machine with [Ollama](https://ollama.com) and one small model. No cloud, no API keys.

> **Status: v0.3 (scope v3).** Deep research, the source panel with feedback, and the reranker are done.
> Chat over the library (M4) is next. See [docs/STATUS.md](docs/STATUS.md) and [docs/SCOPE.md](docs/SCOPE.md).

![A report chapter: every sentence cites a passage, shown in the margin with feedback buttons](docs/images/report-chapter.png)

| | |
|---|---|
| **[Quick start](#quick-start)** | clone, `uv run scripts/setup.py`, `uv run scripts/start.py` |
| **[Setup guide](docs/SETUP.md)** | every step by hand, tested versions, troubleshooting |
| **[User guide](docs/USER_GUIDE.md)** | a research run step by step, reading reports, feedback, the library, settings (with screenshots) |
| **[Case study](docs/CASE_STUDY.md)** | the failure that shaped it, the fix, measured results and limits |

## Case study in 60 seconds

An earlier version wrote a fluent report in which every quote was real and every check passed, and it was still wrong:
a 17B model's training data was presented as advice for a 4B model, a fine-tuning paper as pretraining guidance. A step
that rewrote sources into "facts" in the question's words had quietly changed their subject. The fix was to **remove**
that step: the writer now reads the source passages themselves and code checks every sentence against the passage it
cites. On the same question the new version wrote less, named the real subjects, and said where evidence ran out.

| Final test report | 17 min on a laptop · 5 of 6 sections (the 6th stated as a gap) · 18 sources · 93% of sentences pass the automatic checks* |
|---|---|

\* cited, with their numbers and model names found in the cited passage. This is not a human-verified accuracy score.
**[Read the case study →](docs/CASE_STUDY.md)**

## What a run looks like

1. **Goal** - you type what you want to know. It may ask a few clarifying questions.
2. **Plan** - it splits the goal into sub-questions; you approve or edit them.
3. **Collect** - it searches the web (DuckDuckGo by default, or your SearXNG), arXiv, Europe PMC and Hugging Face,
   shows you the candidates, and saves the ones you pick as markdown in your library.
4. **Retrieve** - for each sub-question: hybrid search (BM25 + vectors, fused with RRF), then a cross-encoder reranker
   keeps the best 8 passages.
5. **Write** - one section per sub-question, written only from its own passages. Code (not another LLM) checks every
   sentence: numbers and model names must appear in the cited passage, citations must point at real passages, weakly
   supported sentences are flagged. A sub-question with no evidence becomes a stated gap, not a padded paragraph.
6. **Review** - in the dashboard you read the report next to its sources and rate them (👍 / 👎 / ⚠ wrong subject),
   flag sentences, and mark the report helpful or not. Feedback is stored with the engine version, so changes can be
   compared before/after.

## How it works

```
collect (web + PDFs) -> library: chunks + BM25 (SQLite FTS5) + vectors
                           |
       retrieve: hybrid (RRF) top ~24 -> reranker (bge-reranker-v2-m3) -> best 8 passages
       each passage carries [document title > section heading]
                           |
       report: one section per sub-question, written from its own passages,
       every sentence cited [C3] and checked in code
```

- Backend: two [LangGraph](https://github.com/langchain-ai/langgraph) graphs in `src/research_assistant/`
  (`goal_graph.py` = deep research; `graph.py` = the earlier quick assistant), served by `langgraph dev`.
- Models: `qwen3.5:4b` for planning and writing (16k context), `qwen3-embedding:0.6b` for embeddings, both via Ollama;
  `BAAI/bge-reranker-v2-m3` on the CPU via Hugging Face transformers.
- Storage: a folder you choose (`VAULT_PATH`, works as an Obsidian vault). Sources and reports are markdown; the
  library index is `<vault>/.kb/library.sqlite`; run traces and feedback are `<vault>/.desk/desk.sqlite`.
  Nothing in the vault is ever deleted by the app (removed items move to `<vault>/.removed`).
- Dashboard: Next.js in `dashboard/` (port 3001), talks to the backend (port 2025) through an API passthrough.

The build story, with the failure that reshaped the design and the measurements behind each choice, is in the
[case study](docs/CASE_STUDY.md); details in [DECISIONS.md](docs/DECISIONS.md), [EVALS.md](docs/EVALS.md) and
[docs/ERROR_LOG.md](docs/ERROR_LOG.md).

## Requirements

| | Minimum | Notes |
|---|---|---|
| RAM | 16 GB | a deep research run uses about **11-12 GB** (model, reranker, PDF conversion); close heavy apps first |
| GPU | optional | an NVIDIA GPU with 8 GB makes writing 5-10x faster; CPU-only works but is slow |
| Disk | ~10 GB | models (~4 GB Ollama + ~2 GB reranker) plus your library |
| Python | 3.12 (3.13 untested, 3.14 fails) | installed with [uv](https://docs.astral.sh/uv/), which fetches 3.12 for you |
| Node.js | 22.18+ | for the dashboard |
| Ollama | recent | <https://ollama.com> |
| OS | Windows 11 (daily use), Linux (CI) | macOS should work but is untested |

## Quick start

You need [uv](https://docs.astral.sh/uv/getting-started/installation/), [Node.js 22.18+](https://nodejs.org) and
[Ollama](https://ollama.com/download) installed, and Ollama running. Then:

```bash
git clone https://github.com/prashanth-ds-ml/research-desk
cd research-desk
uv run scripts/setup.py     # once: packages, models, settings, dashboard build, setup check (~15-30 min, mostly downloads)
uv run scripts/start.py     # every time: starts everything and opens http://127.0.0.1:3001 (Ctrl+C stops it)
```

`setup.py` asks one question (where to keep your sources and reports; Enter = `~/ResearchDesk`), installs exactly the
versions this was developed and tested with (`uv.lock`, `dashboard/package-lock.json`), pulls the two models, writes
the settings files and runs a setup check. It is safe to run again: finished steps are skipped and your settings are
kept. Options: `--no-rerank` for a smaller install without PyTorch, `--yes` to ask nothing.

Then open **Research**, type a goal, and let it collect sources on the first runs (the library starts empty). The
[user guide](docs/USER_GUIDE.md) walks through every page.

Prefer to do it by hand, or something went wrong? The [setup guide](docs/SETUP.md) has every step, the
[tested versions](docs/SETUP.md#tested-versions-use-these-for-the-smoothest-setup) and a troubleshooting table.
On Windows, `scripts/start-research-assistant.ps1` starts both servers in the background (`scripts/register-task.ps1`
registers it to run at log-on).

Command line instead of the dashboard: `uv run python scripts/run_deep_report.py --help`.

## Configuration

All settings live in `.env` (documented in [.env.example](.env.example)); a non-empty environment variable always wins.
The ones you are most likely to change:

| Setting | Default | What it does |
|---|---|---|
| `VAULT_PATH` | - | where sources, reports and the library live |
| `LOCAL_LLM` | `qwen3.5:4b` | the one chat model for every role |
| `RERANK` | `true` | cross-encoder reranking (needs the `rerank` extra) |
| `WRITE_THINKING` / `PLAN_THINKING` | `true` / `false` | let the model think before writing / planning (slower, better) |
| `SEARCH_BACKEND` | `ddgs` | `ddgs` (DuckDuckGo) or `searxng` (set `SEARXNG_URL`) |
| `COLLECT_ALLOW_DOMAINS` / `COLLECT_BLOCK_DOMAINS` | blank | limit where web pages may come from |
| `LANGCHAIN_TRACING_V2` | `false` | optional LangSmith tracing (needs `LANGCHAIN_API_KEY`) |

## Tests

```bash
uv run pytest tests -q          # ~360 offline tests: fake LLM and embeddings, no Ollama or network needed
cd dashboard && npm test        # dashboard unit tests
```

CI runs both, plus lint, a type check and a dashboard build, on every push.

## Known limits

- **Slow on a laptop**: a report takes about 6-30 minutes, longer with many PDFs to convert.
- **One slow PDF can hold up collection** for many minutes; there is no per-source time limit yet.
- **Run one research at a time**: the Stop flag and model-call counters are shared between runs (E-004).
- **If Ollama stops mid-run**, some steps carry on with empty results instead of failing loudly (E-005).
- Small models make mistakes: every sentence is short, cited and checkable, and you can flag it, but errors are not
  guaranteed away. Other open issues: [docs/ERROR_LOG.md](docs/ERROR_LOG.md).
- The **Quick research** page is the earlier v1 assistant (web search loop + notes) and is not part of the v3 checks.
- Desktop notifications are Windows-only.
- Report page display: a `~` in a passage can render as crossed-out text, and the *How it was made* / *Faithfulness*
  boxes still use the earlier label names.

## Repository layout

```
src/research_assistant/   backend: the research graph, library and retrieval, reranker, report writing and checks, collector
dashboard/                Next.js dashboard
scripts/                  setup.py and start.py, setup check, library tools, run audits, experiments (see scripts/README.md)
tests/                    offline test suite (no Ollama or network needed)
evals/                    evaluation data and results behind the case study (see evals/README.md)
docs/                     setup and user guides, case study, progress log, scope, decisions, evals, error log (docs/README.md)
sample_docs/              two small sample documents for the quick assistant's "internal documents" search
```

Changes per release: [CHANGELOG.md](CHANGELOG.md).

## Credits and license

Started from [langchain-ai/local-deep-researcher](https://github.com/langchain-ai/local-deep-researcher) by Lance Martin
(MIT); the quick assistant graph and the web-search helpers still descend from it. The deep research graph, library,
reranking, report checks, collector and dashboard were added here. MIT licensed, see [LICENSE](LICENSE).
