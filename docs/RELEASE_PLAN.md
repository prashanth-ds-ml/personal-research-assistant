# Public release plan: Research Desk (v3)

Drafted 2026-10-22 from three read-only reviews: secrets/personal data, set-up for a stranger, and clutter/dead code.
**Chosen 2026-10-22:** publish v3 as it is, cleaned (Phases 1, 2 minus the demo library, 5 and 6). No refactoring:
Phase 3 fixes and Phase 4 cleanup are left for later and listed in the README's Known limits. Unpushed history
rewritten to remove paths and names; Docker removed; repo renamed to `research-desk`.

## Where things stand

- GitHub repo `prashanth-ds-ml/personal-research-assistant` is **already public**. `origin/main` (e7ccca3, pushed 2026-10-06)
  is v1. Local `main` is 23 commits ahead of it, `v3` 53 ahead, `phase-1a0` unpushed. Working tree clean.
- **Public history is clean**: no API keys or `.env` in any commit, author email is the GitHub no-reply address,
  largest file 542 KB (`uv.lock`). No history rewrite is forced.
- **Unpushed history has small private bits**: absolute home-folder paths (scripts/audit_run.py:27,
  docs/dashboard-redesign-plan.md:100, evals/v3/*.log), the studio name (docs/SCOPE-v2.2, docs/archive/v2.2 phase-4),
  the co-founder's name (docs/archive/v2.2/USER_TESTS.md:43).
- **A stranger cannot run it today**: README is v1, reranker deps missing from a plain install, four different
  default models, Docker/compose v1, CI only on `main`, no first-run library.
- **Real bug for everyone**: root `.gitignore` rule `library/` hides `dashboard/src/app/library/page.tsx` and
  `dashboard/src/app/api/library/doc/route.ts`. A fresh clone's Library page is a 404.

## Phase 0: owner actions (no code)

1. Rotate the LangSmith key that was printed in an old session (also in `dashboard/.env.local`).
2. Answer the decisions at the end of this file.

## Phase 1: privacy and history (before anything is pushed)

1. Replace personal paths with `VAULT_PATH`/placeholders; drop the studio and co-founder names from docs.
2. Rewrite only the **unpushed** commits with `git filter-repo --replace-text` (paths, two names) so the old commits
   don't carry them. `origin/main` is untouched, so no force-push of public history. Backup branch first.
3. `.gitignore`: `library/` -> `/library/`; add `*.log`, `*.sqlite*`, `*.db`, `.env.*` with `!.env.example`.
   Commit the two missing dashboard files.

## Phase 2: make it run for a stranger (the main work)

1. **One set of defaults**: `qwen3.5:4b` + the embedding model everywhere: configuration.py:40, doctor.py:29,
   dashboard/src/lib/system.ts:51, docker-compose.yml, .env.example.
2. **Dependencies**: put the reranker's `torch`/`transformers` in a declared extra (or make the reranker fall back to
   off with a clear message when they are missing). Declare `psutil`. Add `engines` (Node >= 22.18) to package.json.
   Pin Python to what CI tests.
3. **Install path**: `uv sync` + `npm ci`, one start script for Windows and one for Linux/macOS that starts backend
   and dashboard. `.env.example` complete (RERANK_MODEL, KB_PATH, dashboard vars), tracing off by default.
4. **Doctor** checks everything a run needs: Ollama + models pulled, reranker deps + model, docling, Node,
   `langgraph_api` import, free RAM vs the real 11-12 GB need.
5. **First run**: a `scripts/demo_library.py` that downloads ~10 openly licensed arXiv papers on one topic into the
   vault and indexes them, so the first deep report works without web collection. Plus one committed example report
   (from that library) so people can see output before installing.
6. **Docker/compose**: update to v3 or remove. Recommendation: remove for now and say "native install only";
   a stale Docker file is worse than none.
7. **CI**: run on PRs and all branches; Python tests + `npm test` (include desk.test.ts) + `npm run build`.
   Drop the compose-build job if Docker is removed.

## Phase 3: fixes that bite users

1. Per-source time limit in `collector.collect_selected` (one PDF blocked a run for 17 min on 2026-10-22).
2. E-005: a dead Ollama must fail the run loudly, not pass plan/coverage silently.
3. E-004: per-run `STOP`/`LLM_STATS` instead of module globals (two runs interfere).
4. Replace the 11 bare `print(` warnings with `logging`.
Other open items (E-002, E-003, E-006, E-007, E-010) go in the README's Known limits.

## Phase 4: cleanup

- **Remove legacy v1 code** (decision 2): fact extraction / LLM judge path in deep_report.py (:717-1000, :1117,
  :1358-1432), the v1 `research_assistant` graph (graph.py, lmstudio.py, notifications.py, comparison prompts,
  `/new` quick research page), `--facts` flag and their tests. Fewer lines to read, one clear product.
- **docs/**: keep CASE_STUDY, DECISIONS, ERROR_LOG, SCOPE, STATUS, EVALS (trimmed to v3). Move the 12 dated or
  superseded docs and BENCHMARKS.md to `docs/archive/`. Move CLAUDE.md files out of the root (or delete);
  delete `dashboard/AGENTS.md` boilerplate.
- **scripts/**: keep the 11 used ones; move the v2 judge/faithfulness scripts and one-off experiments to
  `scripts/archive/`. **evals/**: keep v3 + retrieval results; archive the v2 fact/judge files; delete `v3/*.log`.
- Local only (not in git): delete `report_*.md`, `.next-dev` (579 MB), stale `.next`.

## Phase 5: presentation

- New README: what it is, 3 screenshots, architecture diagram, hardware needs (16 GB+ RAM, 11-12 GB free per run;
  GPU optional but 5-10x faster), quick start, Known limits, credits.
- LICENSE: keep MIT and Lance Martin's line, add the owner's. "Started from langchain-ai/local-deep-researcher"
  (about 1,500 of ~7,800 lines still descend from it; fewer after Phase 4). Fix pyproject description/authors.
- GitHub description: "Local deep-research desk (LangGraph + Ollama, one 4B model): collects web pages and PDFs
  into a private hybrid-search library and writes reports where every sentence cites a source passage."
- Rewrite dashboard/README.md; add a short CHANGELOG (v1 -> v3).
- Dependabot: merge python-dotenv, actions v7, react/react-dom 19.3 together; close eslint 10, typescript 7,
  @types/node 26 and add ignore rules for those majors.

## Phase 6: verify and publish

1. All Python tests (363) and dashboard tests (22) pass; `npm run build` passes.
2. **Fresh-clone test**: clone into an empty folder, follow only the README, run the demo library and one deep
   report end to end. Anything the README didn't say gets fixed. (Needs the GPU power cap fixed and ~12 GB free RAM.)
3. Merge `v3` into `main` (fast-forward), push, tag `v0.3.0`, GitHub release notes. `phase-1a0` stays local.

## Decisions for the owner

1. **History**: rewrite the unpushed commits to remove paths and names (recommended), or push as-is with only a
   cleanup commit on top (the old commits would still show them)?
2. **Legacy v1 quick research / comparison graph**: remove (recommended), or keep labelled "legacy"?
3. **Docker**: remove for now (recommended), or update and test it?
4. **Platforms**: Windows + Linux (recommended; macOS "should work, untested"), or Windows only?
5. **Repo name**: rename to `research-desk` (GitHub redirects the old URL), or keep `personal-research-assistant`?
6. **Timing**: release now as v0.3 with M4 chat listed as "next", or wait for M4?
