# Setting up Research Desk

From zero to your first report, on Windows or Linux (macOS should work the same way but is untested).
About 30 minutes, most of it downloads. When it runs, continue with the [user guide](USER_GUIDE.md).

## 1. Check your machine

| | Needed | Why |
|---|---|---|
| RAM | 16 GB or more | a run uses about **11-12 GB** (model ~8 GB in Ollama, reranker and PDF conversion ~3 GB) |
| GPU | optional; NVIDIA with 8 GB recommended | writing is 5-10x faster on a GPU; CPU-only works but a report can take an hour or more |
| Disk | ~10 GB free | models (~4 GB Ollama, ~2 GB reranker) plus PyTorch and your library |
| Internet | for installing, for the one-time reranker download, and for collecting sources | everything else runs offline |

## 2. Install the tools

| Tool | Version | Get it |
|---|---|---|
| Git | any | <https://git-scm.com> |
| uv (Python manager) | recent | <https://docs.astral.sh/uv/getting-started/installation/> (it installs Python for you) |
| Node.js | **22.18 or newer** | <https://nodejs.org> (check: `node --version`) |
| Ollama | recent | <https://ollama.com/download> |

Windows: install all four, then open a **new** PowerShell window so they are on the PATH. The commands below work in
PowerShell and in bash.

### Tested versions: use these for the smoothest setup

Research Desk was developed and used daily with exactly the versions below. **Install with `uv sync` and `npm ci`
(not `pip install` or `npm install`)**: they read the lock files (`uv.lock`, `dashboard/package-lock.json`) and install
the very same package versions we ran, so you get the setup that is known to work. Newer versions may work too, but
they are not tested; if something breaks after an upgrade, go back to these.

| Component | Tested version | Notes |
|---|---|---|
| OS | Windows 11 | CI also runs the tests on Ubuntu |
| Python | 3.12.13 | pinned in `.python-version`; supported range 3.12-3.13 (3.14 fails: `tiktoken` has no wheel) |
| uv | 0.11.7 | |
| Node.js / npm | 24.15.0 / 11.12.1 | 22.18+ works (CI uses 22) |
| Ollama | 0.40.8 | |
| Chat model | `qwen3.5:4b` (id `2a654d98e6fb`, 3.4 GB) | `ollama pull qwen3.5:4b` |
| Embedding model | `qwen3-embedding:0.6b` (id `ac6da0dfba84`, 639 MB) | the library index is built with it; changing it needs a rebuild |
| Reranker | `BAAI/bge-reranker-v2-m3` | downloaded from Hugging Face on first use |
| Key Python packages | langgraph 1.2.12 · langchain 1.4.2 · langchain-ollama 1.1.0 · langgraph-cli 0.4.32 / langgraph-api 0.15.1 · torch 2.14.0 · transformers 5.17.0 · docling 2.131.0 · trafilatura 2.2.0 · ddgs 9.16.0 | all ~260 packages are pinned in `uv.lock` |
| Key dashboard packages | next 16.3.6 · react 19.2.8 · @langchain/langgraph-sdk 1.12.0 · typescript 5.9.3 | all ~520 packages are pinned in `package-lock.json` |
| GPU | NVIDIA RTX 5050 Laptop (8 GB), 24 GB RAM | |

Ollama model ids: `ollama list` shows them; the same tag can point to a newer build later, which may behave slightly
differently.

## 3. Get the code and install

```bash
git clone https://github.com/prashanth-ds-ml/research-desk
cd research-desk

uv sync --extra dev --extra rerank
```

This creates `.venv` in the repo folder (on Python 3.12, pinned in `.python-version`; uv downloads it if you do not
have it) with the backend, the `langgraph dev` server, the test tools (`dev`) and
PyTorch + transformers for the reranker (`rerank`, the large part).

Optional extras:

- `--extra docling`: better PDF conversion (keeps tables and headings). Without it PDFs are read as plain text with
  pypdf. It is large and pulls in more of PyTorch. Install with `uv sync --extra dev --extra rerank --extra docling`.
- No room for PyTorch? Leave out `--extra rerank` and set `RERANK=false` in step 5. Reports still work; ranking of
  passages is a bit worse.

## 4. Get the models

Start Ollama (on Windows it runs in the tray after installing; on Linux `ollama serve` or the system service), then:

```bash
ollama pull qwen3.5:4b              # plans and writes (3.4 GB)
ollama pull qwen3-embedding:0.6b    # embeddings for search
```

The reranker (`BAAI/bge-reranker-v2-m3`, ~2 GB) downloads from Hugging Face by itself on the first research run and
is cached in `~/.cache/huggingface`.

## 5. Settings

Pick a folder for your research, for example `C:\Users\you\ResearchDesk` or `/home/you/ResearchDesk`. Sources,
reports and the library index go there; it is created if it does not exist and can be opened as an Obsidian vault.

```bash
cp .env.example .env
cp dashboard/.env.example dashboard/.env.local
```

Edit **both** files and set the same folder:

```
VAULT_PATH=C:\Users\you\ResearchDesk
```

Everything else has working defaults. Useful ones in `.env` (all documented in [.env.example](../.env.example)):
`RERANK=false` without the reranker extra, `SEARCH_BACKEND=searxng` + `SEARXNG_URL` if you run SearXNG,
`COLLECT_EUROPEPMC=False` for software topics, `CONTACT_EMAIL` (sent in the fetcher's User-Agent so site owners can
reach you).

## 6. Build the dashboard

```bash
cd dashboard
npm ci
npm run build
cd ..
```

## 7. Check everything

```bash
uv run python scripts/doctor.py
```

It checks `.env`, the vault folder, Ollama and both models, the reranker libraries, the GPU's power limit, free memory
and the two ports, and prints a fix for anything wrong. Exit code 1 means something must be fixed; warnings are fine
(the ports warn until you start the app in step 8).

## 8. Start it

Two terminals, both in the repo folder:

```bash
uv run langgraph dev --no-browser --no-reload --port 2025
```

```bash
cd dashboard
npm run start
```

Open <http://127.0.0.1:3001>. The front page's *Before you begin* box should show the research engine running and
Ollama with the models. Your first goal: let it collect sources (the library starts empty). See the
[user guide](USER_GUIDE.md).

Windows, without terminals: `scripts/start-research-assistant.ps1` starts both in the background (logs in `logs/`), and
`scripts/register-task.ps1` registers it to start at log-on.

To stop: Ctrl+C in each terminal.

## 9. Optional: run the tests

```bash
uv run pytest tests -q          # ~390 offline tests, no Ollama or network needed (about 2 minutes)
cd dashboard && npm test        # dashboard unit tests
```

## Updating

```bash
git pull
uv sync --extra dev --extra rerank
cd dashboard && npm ci && npm run build && cd ..
```

Then restart both. Do not rebuild the dashboard while a research run is in progress.

## Troubleshooting

| Problem | What to do |
|---|---|
| Doctor: *Ollama not reachable* | Start Ollama (tray app on Windows, `ollama serve` on Linux). If it runs elsewhere, set `OLLAMA_BASE_URL` in both env files. |
| Doctor: *Model ... not installed* | Run the `ollama pull` command it prints. |
| Doctor: *RERANK is on but torch ... is not installed* | `uv sync --extra dev --extra rerank`, or `RERANK=false` in `.env`. |
| Doctor: *power limit ... W against a default of ... W* | The GPU is power-capped: plug in the charger, use the laptop's performance mode. Runs are 5-10x slower otherwise. |
| Dashboard says the research engine is not running | Start `langgraph dev` (step 8). If it runs on another port, set `LANGGRAPH_API_URL` in `dashboard/.env.local`. |
| Dashboard shows no reports or library | `VAULT_PATH` differs between `.env` and `dashboard/.env.local`. Make them the same and restart both. |
| `langgraph dev` fails on start with an import error | The venv has mismatched packages. Run `uv sync --extra dev --extra rerank` again; do not mix in packages installed with plain `pip`. |
| `npm test` fails on `.ts` files, or the build complains about Node | Node is older than 22.18. Update Node. |
| Port 2025 or 3001 already in use | Stop the other program, or start on another port (`--port` for the backend, `-p` in `dashboard/package.json` for the dashboard) and update `LANGGRAPH_API_URL` / `NEXT_PUBLIC_API_URL`. |
| A run is very slow or stops partway | Check free memory (front page or doctor): close large apps. The first run also downloads the reranker (~2 GB). |
| Collecting hangs on one source for a long time | A large PDF is being converted; there is no per-source time limit yet. Wait, or stop the run and collect fewer PDFs. |
| A setting changed in the dashboard has no effect | Settings are written to `.env`; restart `langgraph dev`. |
| PDF tables come out garbled | Install the `docling` extra (step 3). |
