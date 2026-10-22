## What and why

<!-- What does this change, and what problem does it solve? Link the issue if there is one. -->

## How it was tested

<!-- Tests added or changed; measurements (docs/EVALS.md) if it changes retrieval or writing. -->

## Checklist

- [ ] `uv run ruff check src tests scripts evals` and `uv run pytest tests -q` pass
- [ ] Dashboard: `npx tsc --noEmit`, `npx eslint src`, `npm test`, `npm run build` pass (if the dashboard changed)
- [ ] Docs updated where users would notice (USER_GUIDE, SETUP, CHANGELOG), and ERROR_LOG / DECISIONS / EVALS where relevant
- [ ] No secrets, personal paths or private data in the diff
