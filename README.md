# Personal Research Assistant

A fully local, personalized research agent. Fork of
[langchain-ai/local-deep-researcher](https://github.com/langchain-ai/local-deep-researcher)
that archives everything it finds, writes structured reports into an Obsidian
vault, uses that vault as context for future research, and evolves a profile
of what you're interested in over time — all running on your own machine
against Ollama, no API keys or cloud services required (except optional
LangSmith tracing).

> Every model/config choice below was benchmarked against this graph's actual
> prompts, not assumed - see [BENCHMARKS.md](BENCHMARKS.md) for the methodology
> and results, and [DECISIONS.md](DECISIONS.md) for the non-obvious bugs hit
> along the way and how they were diagnosed.

## The problem this solves

The stock research agent is a good demo, but it throws away everything
interesting the moment a run finishes: the full text of every page it read,
the reasoning behind its follow-up queries, any sense of what *you*
specifically care about. Run it twice on related topics and it starts from
zero both times.

This fork turns it into a tool you'd actually use daily: a personal "second
brain" research assistant that gets better at helping you specifically the
more you use it, with a permanent, searchable, linkable archive of every
source it ever read.

## How it works

Same iterative loop as the original (`generate query -> search -> summarize
-> reflect on gaps -> repeat`), extended with five stages wrapped around it:

```
START
  -> load_profile            read your evolving profile note (or bootstrap one)
  -> retrieve_vault_context  find relevant prior research from your own notes
  -> plan_research           detect "X vs Y" comparisons (native tool-calling)
       --single topic--> generate_query -> web_research -> summarize_sources
                            -> reflect_on_summary --loop--> web_research
       --2+ things to compare--> parallel_research  each researched independently,
                                   concurrently (own copy of the loop above, per entity)
  --done--> finalize_summary   structured report, written to your vault
              -> update_profile   appends a dated session-log entry
                 -> notify_complete  native Windows toast when done
                    -> END
```

- **Source archive**: every page's full content (not just the truncated
  snippet used in the prompt) is saved as its own markdown file with
  frontmatter (url, title, query, fetched date) under `Sources/`.
- **Structured reports**: `Research/` gets a `## Key Findings` / `## Open
  Questions` / `## Sources` note per topic, with working relative links to
  the archived sources. Each Open Question includes a `**Current best
  guess:**` - a tentative, clearly-unverified answer from the model's own
  knowledge - so a note is actually useful to build on next time, not just a
  list of things that weren't figured out. Every report page also has a
  "Continue researching this topic" button that jumps straight back into
  "New Research" with the topic prefilled.
- **Comparison mode**: `plan_research` detects when a topic names 2+ things
  to compare ("X vs Y vs Z") using real multi-tool-calling (not a workaround)
  - benchmarked across 8 local models on both a real 3-way comparison prompt
  and a plain single-topic prompt; `llama3.1:8b` (our default) got both
  exactly right and fastest, so no model swap was needed. Each entity then
  gets researched independently and *concurrently* (`asyncio.to_thread`, one
  full copy of the research loop per entity, own `Sources/<entity>/`
  subfolder), and the report gets one `##` section per entity plus a
  synthesized `## Comparison` section - not just N summaries pasted together.
- **Vault-as-context**: before researching, it embeds and searches your
  existing `Research/` notes so it builds on prior work instead of repeating
  it.
- **Evolving profile**: `Profile.md` has a human-owned `## Standing
  Preferences` section (the assistant never touches it) and an
  assistant-owned, append-only `## Session Log` that grows a dated entry
  after every run.
- **Notification**: a native Windows toast fires when a run finishes,
  clicking it opens the report.
- **Dashboard**: a small Next.js app (`dashboard/`) showing research history
  (read straight from the vault - not from LangGraph's own thread storage,
  which doesn't survive restarts), a form to start new research with live
  status, a live pipeline graph, a knowledge graph of your notes, and your
  profile note. Each report also embeds its real LangSmith trace timeline.

## Setup

1. **Ollama models**: `ollama pull llama3.1:8b` (chat), `ollama pull
   qwen3-embedding:0.6b` (vault embeddings). `llama3.1:8b` was picked by benchmarking 7 local models against this
   graph's actual prompts, not by assumption - see [BENCHMARKS.md](BENCHMARKS.md)
   for the full methodology and results. Swap `LOCAL_LLM` in `.env` for
   anything else you have pulled - it's a one-line change.
2. **Python environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -e ".[dev]"
   ```
3. **`.env`**: `cp .env.example .env`, then set `VAULT_PATH` to an Obsidian
   vault on your machine (a new empty folder is fine - it bootstraps
   `Profile.md` and the `Research`/`Sources` subfolders on first run). Note
   that a non-empty env var always wins over dashboard/UI overrides (an empty
   one counts as unset), and the dashboard may only change a few per-run options
   (see `PER_RUN_KEYS` in `configuration.py`) - that's why
   `MAX_WEB_RESEARCH_LOOPS` is deliberately absent from `.env.example`.
4. **Dashboard**: `cd dashboard && npm install && cp .env.example .env.local`,
   then point `VAULT_PATH` at the same vault as step 3.

## Running it

**Automatically** (recommended): a Windows Task Scheduler task
(`ResearchAssistantAutoStart`) starts both processes at logon. Logs land in
`logs/` and `dashboard/logs/`.

**Manually**, for development:
```powershell
# Terminal 1 - backend (port 2025; see "Known issues" below for why not 2024)
langgraph dev --no-browser --no-reload --port 2025

# Terminal 2 - dashboard (port 3001)
cd dashboard
npm run dev
```
Then open http://localhost:3001.

To stop auto-start: `Unregister-ScheduledTask -TaskName ResearchAssistantAutoStart`.

## Searching internal documents (not the web)

The original customer story: *"dig through our scattered internal docs and
give me a cited summary."* Point the assistant at a folder of PDF / Markdown /
text files and it retrieves from those instead of the web. Everything
downstream (summarize, reflect, archive to the vault, cite) is unchanged.

- **Dashboard:** New Research -> Search -> "Internal documents".
- **Config:** `search_api=local_docs` and `DOCS_PATH=/path/to/docs`
  (see `.env.example`; `docs_top_k` / `docs_chunk_size` tune retrieval).
  Leave `SEARCH_API` unset in `.env` or it overrides the dropdown.
- **Citations** look like `doc://handbook.pdf/p3-c2` (file, page, chunk) and
  each retrieved chunk is archived under `Sources/` like any web source.
- PDFs are text-extracted per page with `pypdf` (scanned/image-only PDFs
  yield no text and are skipped - OCR is out of scope). The corpus is
  embedded in memory with `EMBEDDING_MODEL` and cached until files change.
- `sample_docs/` holds a demo set (the AcmeCorp employee handbook PDF and an
  incident-response runbook).

## Docker

One command runs the backend (port 2025) and dashboard (port 3001):

```bash
ollama pull llama3.1:8b && ollama pull qwen3-embedding:0.6b   # Ollama runs on the host
docker compose up --build
```

- Dashboard: <http://localhost:3001> - LangGraph API: <http://localhost:2025>
  (both published on 127.0.0.1 only; nothing else on your network can reach them)
- The vault is a bind mount (`VAULT_DIR`, default `./vault`) shared by both
  containers; your documents mount read-only from `DOCS_DIR` (default
  `./sample_docs`) at `/docs`. Example:
  `VAULT_DIR=~/ObsidianVault DOCS_DIR=~/company-docs docker compose up`
- Containers reach Ollama at `host.docker.internal:11434`. Model override:
  `DOCKER_LOCAL_LLM=qwen3:8b docker compose up`. Port clash on 3001:
  `DASHBOARD_PORT=3002`.
- The host `.env` is deliberately not passed in (Windows paths, secrets).
  Note compose still reads `./.env` for `${...}` interpolation, so the compose
  file only interpolates `DOCKER_*` / `VAULT_DIR` / `DOCS_DIR` / `DASHBOARD_PORT`
  (`DOCKER_LIBRARY_FOLDERS`, `DOCKER_CONTACT_EMAIL` reach deep research).
- Windows toast notifications are disabled in containers.

## Deep research mode (goal -> long cited report)

A second graph, `deep_research`, for questions that deserve a proper report:
you give a **goal**, and the assistant

1. **asks clarifying questions** (audience, scope, what the decision is) and
   pauses for your answers,
2. **plans** the research (sub-questions + a report outline) and pauses for you to
   **approve or revise** it - nothing expensive runs before that,
3. **retrieves** from your document library with hybrid search (BM25 + vectors),
4. **extracts** facts passage by passage; a fact survives only if its quote appears
   **verbatim** in the source *and* a second model call judges the passage supports it,
5. **writes** the report section by section, each seeing only its own evidence
   (plus a recommendations section synthesised from the others), with tables and
   `[E#]` citations,
6. saves it to the vault with an evidence appendix mapping every citation to its
   quote and source.

Everything runs on local models (about 165 model calls, ~11 minutes on an 8 GB GPU
for a 6-question report). Use it from the dashboard's **Deep Research** page, or
build the library and run it from the command line:

```bash
# PDF/DOCX -> markdown (tables kept) -> hybrid search index; incremental
pip install -e ".[docling]"
python scripts/ingest_library.py library/ --kb library_kb.sqlite --md-out library_md   # --md-out must be OUTSIDE library/

# goal -> report (no questions asked; the dashboard/API adds the two pauses)
python scripts/run_deep_report.py "Should we use hybrid retrieval for ...?" --kb library_kb.sqlite     --write-model gemma4:e4b
```

How well it works is measured in [EVALS.md](EVALS.md) (retrieval ablation: hybrid
80% recall@1 vs 68% BM25 vs 48% dense; report-quality progression across fixes;
faithfulness-judge scoring against human labels) and the model choices in
[BENCHMARKS.md](BENCHMARKS.md). For deploying it for someone else, see
[docs/deployment-runbook.md](docs/deployment-runbook.md) and
[docs/discovery-questionnaire.md](docs/discovery-questionnaire.md).

### How it grows as you use it

The library and your feedback are what make it better over time; no retraining involved.

- **Two source folders in your vault.** `Sources/` holds pages the quick assistant archived;
  `Library/` holds your PDFs and anything the fetcher saves. At the start of every deep-research run
  the assistant indexes any new or changed files in both (unchanged files are skipped by hash, so
  it is free when nothing changed): drop a PDF into `Library/`, start a run, and it is searchable.
- **Optional source fetching.** Tick *Fetch new open-access papers first* on the Deep Research page
  (or run `python scripts/collect.py "<question>"`). After you approve the plan it searches arXiv
  and Europe PMC (official APIs; arXiv paced at one request per 3 seconds; Europe PMC open-access
  full text only), has the local model score each candidate 0-3 *before* downloading, keeps only the
  ones that directly answer the question (score 3; configurable, since a looser bar lets tangential
  papers into the library for good) with provenance (source, date, question, licence note) in `Library/<date>-<goal>/`,
  keeps the original PDFs in `raw/`, writes a `manifest.json` listing every candidate and why it was
  kept or skipped, and never saves the same paper twice. You can also paste page or PDF URLs
  (robots.txt is honoured; login/paywalled pages are skipped). It is not a general crawler.
- **One-click feedback.** Each report page asks *Was this report useful?* (plus an optional note).
  The rating is stored in the report's own frontmatter, and the planner is told about your last five
  ratings next time ("the report X was not useful: too generic, wanted numbers").

**Honest limits:** the output is a cited first draft for an expert, not a finished
document. Local 8B models still occasionally merge two true findings into a false
one, recommendations are generic, and the faithfulness judge has not yet been
scored against human labels (the sheet is generated; see EVALS.md).

## Testing

```bash
pytest tests
```

Offline (no Ollama, no network): covers source archiving, report links,
vault retrieval, the internal-doc retriever, and the append-only profile guarantee. See
[EVALS.md](EVALS.md) for what these do and don't verify.

## Folder layout

```
src/research_assistant/   the LangGraph app (renamed from ollama_deep_researcher to
                           avoid a package-name collision if you also have the
                           original tutorial installed in the same environment)
  graph.py                 nodes + wiring
  vault.py                 all Obsidian I/O: archiving, reports, profile, retrieval
  documents.py             internal-doc retriever (PDF/MD/TXT -> chunks -> embeddings)
  knowledge.py             persistent hybrid-search knowledge base (Docling -> chunks -> SQLite FTS5 + vectors)
  deep_report.py           plan -> extract -> verify -> write pipeline (testable with fake LLMs)
  goal_graph.py            the deep_research LangGraph graph (clarify / approve interrupts)
  notifications.py         Windows toast wrapper
dashboard/                 Next.js app (history, new-research form, profile view)
sample_docs/               demo internal documents for search_api=local_docs
evals/                     retrieval question set, results, faithfulness labelling sheet
docs/                      deployment runbook, customer discovery questionnaire
Dockerfile, docker-compose.yml, dashboard/Dockerfile   container setup
scripts/                   start-research-assistant.ps1, register-task.ps1,
                           benchmarks/ (model-selection scripts)
tests/                     offline pytest suite for vault.py (`pytest tests`)
BENCHMARKS.md              model-selection methodology and results
DECISIONS.md               non-obvious bugs and how they were diagnosed
EVALS.md                   reliability checks + demo script
```

## Known issues / accepted limitations

- **DuckDuckGo search can still be flaky, occasionally.** `utils.py` uses
  `ddgs` (the actively-maintained rename of `duckduckgo_search`, which was
  silently returning empty/irrelevant results - confirmed via isolated
  testing, unrelated to any code here). `ddgs` is far more reliable, but the
  underlying free HTML-scraping backend can still rate-limit occasionally.
  The pipeline degrades gracefully either way (empty research loop -> report
  with no archived sources for that run, not a crash).
- **Ports 2024/3000 avoided.** During development these got stuck with a
  genuinely orphaned OS-level socket (confirmed via `Get-NetTCPConnection`/
  `Get-CimInstance` - no real process backed the listener). This project
  standardizes on 2025/3001 instead; there's no need to switch back.
- **Env vars always beat per-run dashboard overrides** (see
  `Configuration.from_runnable_config`: non-empty env > `configurable` (only the keys in `PER_RUN_KEYS`) > default).
  `.env` deliberately leaves `MAX_WEB_RESEARCH_LOOPS` unset so the dashboard's
  loop-count input can actually take effect per run - don't add them back to `.env` unless you
  want to hard-lock that setting for every run regardless of the UI.
- **In-memory backend**: `langgraph dev` doesn't persist runs across
  restarts. If it restarts mid-run, that run is simply lost - the vault
  (not LangGraph threads) is the durable source of truth for history.
- **Web PDFs/binary sources** aren't text-extracted, just stubbed with a
  note and the search snippet. (PDFs in the internal-docs folder *are*
  parsed - see above - but scanned PDFs need OCR, which isn't built.)
- **Internal-doc retrieval is a plain vector search** over an in-memory
  index rebuilt when files change: fine for hundreds of documents, not
  millions. No reranking, no per-user access control.
- **Docker uses `langgraph dev`** (in-memory runs, lost on container
  restart), same as the local setup; the vault is the durable record.

## Acknowledgments

Forked from [langchain-ai/local-deep-researcher](https://github.com/langchain-ai/local-deep-researcher).
Comparison mode's prompt pattern was adapted from
[langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research)
after investigating its architecture directly (see `DECISIONS.md` for why its
control flow wasn't adopted wholesale).
