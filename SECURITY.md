# Security

## Reporting a vulnerability

Please report security problems privately through GitHub: the repository's **Security** tab → **Report a
vulnerability**. Do not open a public issue for them. You should get a reply within a week.

## How Research Desk is meant to run

Research Desk is a single-user, local application. Knowing its design helps judge what is and is not a vulnerability:

- **Local only.** The backend (`langgraph dev`, port 2025) and the dashboard (port 3001) listen on `127.0.0.1` and have
  **no login**. Do not expose them to a network or the internet (port forwarding, a reverse proxy, `-H 0.0.0.0`); anyone
  who can reach them can run research, read your library and change settings.
- **Models run on your machine** through Ollama. Nothing is sent to a cloud model. Optional LangSmith tracing is off by
  default; when on, run traces go to LangSmith.
- **Fetching sources.** The collector fetches web pages and papers you approve. It only fetches `http(s)` addresses that
  resolve to public IPs (no localhost or private networks), respects `robots.txt` and caps download size.
- **Secrets** live in `.env` and `dashboard/.env.local`, which git ignores. Never commit them. The dashboard's settings
  page writes only a fixed list of non-secret settings to `.env`.
- **Your files stay in your vault folder.** The app never deletes library content (removed documents move to
  `<vault>/.removed`).

## Supported versions

Only the latest release gets fixes.
