# Dashboard

Next.js 16 (App Router) frontend for the personal research assistant. See the
[repo root README](../README.md) for what this project does overall - this
file just covers the dashboard itself.

## Pages

| Route | What it does |
|---|---|
| `/` | Research history, read straight from the Obsidian vault's `Research/` folder (not from LangGraph's own thread storage, which doesn't survive restarts) |
| `/new` | Start a new research topic, with live streaming status, a Debate mode toggle, and comparison-mode awareness |
| `/graph` | The actual compiled LangGraph structure (nodes + edges), fetched live from the running backend |
| `/knowledge` | A force-directed graph of your research notes, connected by embedding similarity |
| `/profile` | Read-only view of the evolving `Profile.md` |
| `/research/[slug]` | A single report, with its real LangSmith trace timeline embedded and a "Continue researching this topic" link back to `/new` |

## Architecture notes

- `src/app/api/[..._path]/route.ts` proxies every request to the local
  `langgraph dev` server (`LANGGRAPH_API_URL`), so the client SDK/`useStream`
  hook never needs to know its URL or API key directly.
- `src/lib/vault.ts` and `src/lib/langsmith.ts` are the two places server
  code reads external state: the Obsidian vault (filesystem) and LangSmith
  (REST API), respectively. Both are read-only from the dashboard's side -
  the backend graph is what writes to the vault.
- `src/lib/embeddings.ts` calls Ollama directly (not through the backend)
  to compute the knowledge graph's similarity edges.

## Development

```bash
npm install
cp .env.example .env.local   # then edit VAULT_PATH etc.
npm run dev                  # http://localhost:3001
```

`npm run build && npm run start` for the same production mode the auto-start
script (`../scripts/start-research-assistant.ps1`) uses - dashboard code
changes need a rebuild before they'll show up there.
