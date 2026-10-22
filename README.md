# Research Desk

Local deep research that builds your own private library. You give it a goal; it plans sub-questions, collects web
pages and papers, indexes them, and writes a short report in which **every sentence cites a source passage**. Everything
runs on your machine with [Ollama](https://ollama.com) and one small model. No cloud, no API keys.

> **Status: v0.3 (scope v3).** Deep research, the source panel with feedback, and the reranker are done.
> Chat over the library (M4) is next. See [docs/STATUS.md](docs/STATUS.md) and [docs/SCOPE.md](docs/SCOPE.md).

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

Example (from [EVALS.md](EVALS.md)): *Local private RAG system design for small teams* - 5 of 6 sections answered
(the sixth an honest gap), 2,979 words, 18 sources, 93% of 155 sentences passed every check, 17 minutes.

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

Design decisions and the bugs found along the way are in [DECISIONS.md](DECISIONS.md),
[docs/ERROR_LOG.md](docs/ERROR_LOG.md) and the build story in [docs/CASE_STUDY.md](docs/CASE_STUDY.md).

## Requirements

| | Minimum | Notes |
|---|---|---|
| RAM | 16 GB | a deep research run uses about **11-12 GB** (model, reranker, PDF conversion); close heavy apps first |
| GPU | optional | an NVIDIA GPU with 8 GB makes writing 5-10x faster; CPU-only works but is slow |
| Disk | ~10 GB | models (~4 GB Ollama + ~2 GB reranker) plus your library |
| Python | 3.10+ (tested on 3.12) | installed with [uv](https://docs.astral.sh/uv/) |
| Node.js | 22.18+ | for the dashboard |
| Ollama | recent | <https://ollama.com> |
| OS | Windows 11 (daily use), Linux (CI) | macOS should work but is untested |

## Install

```bash
git clone https://github.com/prashanth-ds-ml/research-desk
cd research-desk

# Python backend (dev = langgraph dev server + tests; rerank = torch + transformers for the reranker)
uv sync --extra dev --extra rerank
# optional, better PDF/table conversion (large, pulls PyTorch):  uv sync --extra dev --extra rerank --extra docling

# Models
ollama pull qwen3.5:4b
ollama pull qwen3-embedding:0.6b

# Settings: set VAULT_PATH in both files to the same absolute folder (it is created if missing)
cp .env.example .env
cp dashboard/.env.example dashboard/.env.local

# Dashboard
cd dashboard && npm ci && npm run build && cd ..

# Check everything (Ollama, models, reranker libraries, vault, memory, GPU, ports)
uv run python scripts/doctor.py
```

No reranker libraries or not enough memory? Set `RERANK=false` in `.env`; reports still work, ranking is a bit worse.

## Run

Two terminals, from the repo folder:

```bash
uv run langgraph dev --no-browser --no-reload --port 2025      # backend
```

```bash
cd dashboard && npm run start                                  # dashboard -> http://127.0.0.1:3001
```

Open <http://127.0.0.1:3001>, go to **Research**, type a goal. Your library starts empty, so tick source collection on
the first runs; later goals reuse what is already in the library. Runs, reports, the library and settings each have
their own page.

On Windows, `scripts/start-research-assistant.ps1` starts both in the background (and `scripts/register-task.ps1`
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

## Repository layout

```
src/research_assistant/   backend: graphs, retrieval (knowledge.py, rerank.py), report writing and checks, collector
dashboard/                Next.js dashboard
scripts/                  doctor, ingest/reindex the library, CLI runs, run audits, experiments
tests/                    offline test suite
evals/                    retrieval question set and experiment results behind the decisions
docs/                     scope, status, error log, case study, design notes (docs/archive = older plans)
```

## Credits and license

Started from [langchain-ai/local-deep-researcher](https://github.com/langchain-ai/local-deep-researcher) by Lance Martin
(MIT); the quick assistant graph and the web-search helpers still descend from it. The deep research graph, library,
reranking, report checks, collector and dashboard were added here. MIT licensed, see [LICENSE](LICENSE).
