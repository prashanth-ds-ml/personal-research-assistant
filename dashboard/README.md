# Dashboard

Next.js 16 (App Router) frontend for Research Desk. See the [root README](../README.md) for what the project does and
how to install it; this file covers the dashboard only.

## Pages

| Route | What it does |
|---|---|
| `/` | Front page: recent runs and reports |
| `/deep` | Start a deep research run: goal, clarifying questions, plan approval, source review, live progress |
| `/runs` | Every run with its status and live view; paused runs can be resumed, running ones stopped |
| `/reports`, `/research/[slug]` | Reports, each next to its source passages with feedback buttons (👍 / 👎 / ⚠, sentence flags, helpful) |
| `/library` | The library: documents, previews, add files, re-index |
| `/knowledge` | A graph of notes connected by embedding similarity |
| `/compare` | Which report issues changed between two runs |
| `/graph` | How a run flows through the pipeline |
| `/new` | Quick research: the earlier v1 assistant (short note in minutes) |
| `/profile`, `/settings` | Profile note; models, sources and quality settings (written to the backend `.env`) |

## Architecture notes

- `src/app/api/[..._path]/route.ts` proxies requests to the local `langgraph dev` server (`LANGGRAPH_API_URL`).
- Server code reads the vault folder (`VAULT_PATH`) directly for reports, run records and the library, and writes
  feedback to `<vault>/.desk/desk.sqlite`.
- Library actions (add, re-index) run the backend's Python scripts; the Python used is `PYTHON_BIN`, else the repo's
  `.venv`, else `python` on the PATH.

## Development

```bash
npm ci
cp .env.example .env.local   # set VAULT_PATH (same as the backend .env)
npm run dev                  # http://127.0.0.1:3001
npm test                     # unit tests (Node 22.18+)
```

`npm run build && npm run start` is the production mode the start script uses; code changes need a rebuild. Do not
rebuild while a research run is live in a running dashboard.
