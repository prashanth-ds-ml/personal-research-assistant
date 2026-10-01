# Deployment runbook

For whoever installs and operates this system. Everything here was exercised
during development; the troubleshooting section lists failures that actually
happened.

## What runs where
```
+------------------ host machine ------------------+
|  Ollama (models, GPU)        :11434              |
|                                                  |
|  docker compose                                  |
|   backend   LangGraph API    :2025  --- /vault   |  <- reports, notes, sources, KB (read/write)
|                                     --- /docs    |  <- your documents (read-only)
|   dashboard Next.js          :3001  --- /vault   |
+--------------------------------------------------+
```
Nothing leaves the machine: models run in Ollama, retrieval uses a local
SQLite file, and the only outbound traffic is optional (web search, LangSmith
tracing). Set `LANGCHAIN_TRACING_V2=false` and use `search_api=local_docs` for
a fully offline deployment.

## Requirements
- Windows 11 or Linux, Docker with Compose v2, Ollama on the host.
- 16 GB RAM minimum (24 GB comfortable). A GPU with 8 GB VRAM runs 8B models
  on-GPU; without a GPU everything still runs but is several times slower.
- Disk: about 10 GB for models, plus the Docling install (about 2 GB) if you
  ingest PDFs/DOCX.

## Install
```bash
ollama pull llama3.1:8b            # planner / extractor / writer default
ollama pull qwen3-embedding:0.6b   # embeddings
ollama pull gemma4:e4b             # optional: a stronger writer (see BENCHMARKS.md)

# PDF/DOCX -> markdown with tables needs Docling (heavy). Opt in at build time:
docker compose build --build-arg INSTALL_DOCLING=true

VAULT_DIR=/path/to/vault DOCS_DIR=/path/to/documents docker compose up -d
```
Dashboard: <http://localhost:3001> - API: <http://localhost:2025>.
Use `DASHBOARD_PORT=3002` if 3001 is taken.

## Load the document library
The library is one SQLite file, `<vault>/.kb/library.sqlite` (or `KB_PATH`). The graph
and every script read the same location. Each folder you ingest is its own namespace,
so adding a folder never removes another's documents, and re-running a folder only
adds, updates or removes that folder's files. Unchanged files (same content hash) are
skipped before the slow conversion step.
```bash
python scripts/ingest_library.py /path/to/documents /path/to/vault/Sources --md-out /path/to/vault/Library
```
`--md-out` also writes each converted document as markdown, so the library is browsable
in Obsidian. It must be a folder that is not itself indexed, otherwise the copies are
indexed again; `<vault>/Library` is the usual choice and is one of the default indexed
folders, which is why deep research keeps it in step automatically. Index the vault's `Sources/` (archived web pages), **not** `Research/`: the
Research notes are model-written reports, and citing them as evidence would make the
assistant cite itself.

PDFs convert with OCR off (about 20 s per paper-sized PDF on CPU); a PDF that yields
almost no text is treated as scanned and converted again with OCR automatically.

## Keeping the library growing
- **Folders:** by default the run indexes `<vault>/Sources` (archived web pages) and `<vault>/Library`
  (your PDFs plus fetched papers). Override with `library_folders` (folders separated by `;`) or
  switch off with `auto_ingest=false`. A folder's name is its namespace in the index, so two folders
  must not share a name.
- **Fetching:** `python scripts/collect.py "<question>" --max 5` or the checkbox on the Deep Research
  page. Set `CONTACT_EMAIL` so site owners can reach you (put in the User-Agent). Sources are kept only if the local model scores them 3 of 3 ("under 3" are dropped) (`fetch_min_relevance`). Each fetch writes
  `Library/<date>-<goal>/manifest.json`: read it to see what was skipped and why. Sources are limited
  to arXiv, Europe PMC open access, and URLs you supply; respect each site's terms; keep fetched
  content private.
- **Feedback:** rating buttons on each report page write `feedback_rating` / `feedback_note` into the
  report file; the planner reads the five most recent. To reset what it has learned, delete those
  lines from the reports.

## Verify it works (10 minutes)
1. `pytest tests -q` - offline suite, no models needed.
2. `python scripts/eval_retrieval.py --kb <kb>` - recall@k on your documents
   (write your own question file first; see `evals/retrieval_qa.json` for the format).
3. In the dashboard: **Deep Research** -> enter a goal -> answer the questions
   -> approve the plan -> wait for the report.

## Operate
| Task | How |
|---|---|
| Add documents | Drop files in `<vault>/Library` (indexed at the start of every deep-research run), or in `DOCS_DIR` (read-only; indexed by deep research because the compose file lists `/docs` in `LIBRARY_FOLDERS`) |
| Change the embedding model | Set `EMBEDDING_MODEL`, then `python scripts/reindex.py --rebuild` (minutes, no PDF conversion). Until then the library refuses to open with a different model |
| Back up | Copy the vault folder (reports, sources, `.kb/library.sqlite`, profile) |
| Move to another machine | Copy the vault; re-pull the models |
| Change models | `DOCKER_LOCAL_LLM`, or per role `DOCKER_PLANNER_MODEL` / `DOCKER_EXTRACTOR_MODEL` / `DOCKER_WRITER_MODEL` (blank = `LOCAL_LLM`), e.g. `DOCKER_WRITER_MODEL=gemma4:e4b docker compose up -d` |
| Run unattended | Per run: `configurable: {ask_clarifying_questions: false, require_plan_approval: false}` in the API call |
| Update | `git pull && docker compose build && docker compose up -d` |

## Troubleshooting (all of these happened)
| Symptom | Cause | Fix |
|---|---|---|
| "Ollama isn't reachable at http://localhost:11434" inside a container | Container's `localhost` is itself | Compose sets `host.docker.internal`; do not override `OLLAMA_BASE_URL` in the host `.env` (compose reads `.env` for interpolation, which once leaked the host value in) |
| Embeddings fail although chat works in Docker | `OllamaEmbeddings` ignored `OLLAMA_BASE_URL` | Fixed: the URL is passed explicitly; if you see it again, check the embedding model is pulled |
| `port is already allocated` on 3001 | Another dashboard instance (e.g. autostart) | `DASHBOARD_PORT=3002` |
| Run dies with "prediction aborted, token repeat limit reached" | Ollama aborts a degenerate generation | Calls are retried with higher temperature and repeat penalty; a call that still fails yields an empty result instead of crashing the run |
| Job killed / machine unresponsive during long runs | Memory pressure (Docling + models + other apps) | Close heavy apps; run models one at a time; `ollama stop <model>` between stages; Docker Desktop idle costs about 1 GB |
| Ollama "connection attempt failed" on `/tokenize` mid-run with qwen3:8b | Model server stalled under load | Re-run; prefer llama3.1:8b for extraction, which was the most stable |
| PDF ingest is very slow | Docling runs on CPU-only PyTorch | Expected (1-4 min/PDF); a CUDA build of PyTorch would speed it up |
| A section says "No supporting evidence" | The library really has none for that question | Add documents (or tick *Find and collect new sources first* and choose from what it finds), or narrow the goal; this is intentional, the system will not invent |
| Fetcher saved nothing | Every candidate scored under 2, or the sites blocked/limited you | Read `manifest.json` in the run's `Library/` folder: each skip has a reason (relevance, robots.txt, paywall, duplicate, too little text) |

## Security notes
- The host `.env` is never copied into images (`.dockerignore`); configuration
  reaches containers only through `docker-compose.yml`.
- Documents mount read-only. Only the vault is writable.
- Reports quote sources verbatim: if sources contain personal data, so can reports.
- There is no authentication on the dashboard or API; bind them to localhost or
  put them behind your own reverse proxy / VPN.
