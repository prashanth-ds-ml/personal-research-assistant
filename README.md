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
  --done--> debate_perspectives  optional: GPU advocate + CPU critic, concurrently
              -> finalize_summary   structured report, written to your vault
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
- **Debate mode** (opt-in checkbox on "New Research"): runs the main model
  as an advocate on GPU and `gemma3:4b` as a critic pinned to CPU
  (`num_gpu=0`) *concurrently* - measured ~3.4x faster than running two
  models sequentially, since they use separate memory pools (VRAM vs.
  system RAM) and don't contend. The critic is deliberately a different
  model family (Google Gemma vs. Meta Llama) - same-family models share
  training data/alignment and produce a much weaker, more agreeable
  "debate." Both voices land verbatim, labeled, in a `## Perspectives`
  section of the report.

## Setup

1. **Ollama models**: `ollama pull llama3.1:8b` (chat), `ollama pull
   qwen3-embedding:0.6b` (vault embeddings), and `ollama pull gemma3:4b`
   (debate mode's CPU-pinned critic - only needed if you use that feature).
   `llama3.1:8b` was picked by benchmarking 7 local models against this
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
   that env vars always win over dashboard/UI overrides (see
   `Configuration.from_runnable_config` in `configuration.py`) - that's why
   `MAX_WEB_RESEARCH_LOOPS` and `ENABLE_DEBATE_MODE` are deliberately absent
   from `.env.example`.
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

## Folder layout

```
src/research_assistant/   the LangGraph app (renamed from ollama_deep_researcher to
                           avoid a package-name collision if you also have the
                           original tutorial installed in the same environment)
  graph.py                 nodes + wiring
  vault.py                 all Obsidian I/O: archiving, reports, profile, retrieval
  notifications.py         Windows toast wrapper
dashboard/                 Next.js app (history, new-research form, profile view)
scripts/                   start-research-assistant.ps1, register-task.ps1
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
  `Configuration.from_runnable_config`: env > `configurable` dict > default).
  `.env` deliberately leaves `MAX_WEB_RESEARCH_LOOPS` and `ENABLE_DEBATE_MODE`
  unset so the dashboard's loop-count input and debate-mode checkbox can
  actually take effect per run - don't add them back to `.env` unless you
  want to hard-lock that setting for every run regardless of the UI.
- **In-memory backend**: `langgraph dev` doesn't persist runs across
  restarts. If it restarts mid-run, that run is simply lost - the vault
  (not LangGraph threads) is the durable source of truth for history.
- **PDFs/binary sources** aren't text-extracted, just stubbed with a note
  and the search snippet - full PDF parsing is out of scope for v1.

## Acknowledgments

Forked from [langchain-ai/local-deep-researcher](https://github.com/langchain-ai/local-deep-researcher).
Comparison mode's prompt pattern was adapted from
[langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research)
after investigating its architecture directly (see `DECISIONS.md` for why its
control flow wasn't adopted wholesale).
