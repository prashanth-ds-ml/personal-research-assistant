# Project 4 close-out review (senior AI engineer lens), 2026-10-01

Method: three independent read-only reviewers (backend and architecture, dashboard and security, setup and packaging), plus my own
checks: 266 offline tests and lint (both pass), and a **literal fresh clone** (`git clone`, new venv, `pip install -e .`, 144 s, then
importing both graphs). Items are tagged **[V]** verified by me, **[R]** reviewer finding read from code and not run, **[U]** unverified.
Cause of the earlier slowdown (system memory) is in `model-memory-plan.md`.

## 1. What the project is, and what exists

A fully local (Ollama, no paid APIs) research assistant with two LangGraph graphs and a Next.js dashboard.

| Area | What is built | Evidence |
|---|---|---|
| Quick assistant (`graph.py`) | Query, search (web or your own documents), summarize, reflect loop; saves notes to an Obsidian vault; evolving profile | Live run, 9 smoke tests |
| Deep research (`goal_graph.py`, `deep_report.py`) | goal -> clarifying questions -> plan -> **coverage check** -> approval -> optional source collecting -> evidence extraction (verbatim quote + judge + on-topic flag) -> gated section writing -> report with status table, labels, one recommendation, sources grouped as PDFs/web/other | 266 tests; v6 run: 66 facts, 12 sources; live runs today |
| Knowledge base (`knowledge.py`) | SQLite FTS5 + vectors, hybrid retrieval, per-folder namespaces, embedding-model guard, rebuild, Docling for PDFs, table-aware chunking | Retrieval eval: hybrid 80% recall@1 vs BM25 68%, dense 48% |
| Collector (`collector.py`, `fetcher.py`) | web (DuckDuckGo or SearXNG) + arXiv + Europe PMC discovery, relevance scoring, review pause, sequential collect to markdown with manifest, SSRF guard, robots.txt | Live: 40 candidates, 2 saved |
| Operations | Run records in the vault, Runs page with live progress, Stop, runaway-call guard, resume from last finished question | Live-tested |
| Dashboard | Reports (deep/quick), Runs, Deep Research, New, Knowledge graph, Profile; proxy with Host/Origin checks; feedback | Type-check, lint, build clean; **not yet clicked through in a browser** |
| Packaging | Dockerfile, compose (loopback ports, healthcheck), CI, MIT licence, `.env.example` | Docker acceptance passed on 30 Sep |
| Evidence | EVALS.md, BENCHMARKS.md, DECISIONS.md, 3 audits | Mixed: see section 5 |

Size: about 5,800 lines of Python in `src/`, 3,600 of tests, 3,100 of dashboard TypeScript; 19 commits; 139 tracked files, none large.

## 2. Verdict
The core idea and the engineering discipline (offline-testable design, fail-closed judging, honest limits, audits) are strong and unusual for a
portfolio project. It is **not yet closeable** for three reasons, all fixable inside 3 days: (a) a stranger cannot get it running from the README;
(b) a few correctness bugs in the newest code (Stop, Windows file races, label logic) undermine claims the README and demo will make; (c) the
quality gate has had **no real end-to-end validation** (one run was cut short by the memory problem), so "the report is now trustworthy" is not yet
a supported statement.

## 3. Must-fix before closing (ordered)

### A. Packaging blockers (a stranger cannot start it)
| # | Finding | Evidence | Fix |
|---|---|---|---|
| A1 | **`langgraph dev` is not installed by the documented install.** The fresh clone has no `langgraph` command; neither `langgraph-cli` nor `langgraph-api` is in `pyproject.toml`; only the Dockerfile installs it. | **[V]** fresh clone venv: no `langgraph.exe` | Add `langgraph-cli[inmem]` to the dev extra (or a `run` extra), regenerate `uv.lock` |
| A2 | **README describes only the quick assistant.** No deep-research quick start, no architecture of the two graphs, stale test and folder sections, dashboard pages table lacks /deep, /runs. | [R] README, dashboard/README | Rewrite the top of the README (section 6) |
| A3 | **Missing prerequisites and models.** README pulls llama and the embedder but `.env.example` sets `WRITER_MODEL=gemma4:e4b`, so the first deep run fails on a missing model. Python 3.10 vs 3.11 vs 3.12 across pyproject, Docker and CI. Node version, Ollama link, model sizes, 8 GB GPU note, and the Docling extra (heavy, downloads weights, contradicts "nothing leaves the machine") are not stated. Compose leaves `DOCKER_WRITER_MODEL` blank. | [R] | Pin Python 3.11+, document models and sizes, default the Docker writer |
| A4 | **No setup or doctor command; first-run failures are raw errors.** Ollama down or a model missing gives an httpx/404 trace mid-run (no preflight except the PowerShell script). | [R] goal_graph.py build_llms | `scripts/doctor.py` (Ollama, models, VAULT_PATH, ports, free RAM) called by the app's first step and a Makefile |
| A5 | **The demo corpus is not in the repo.** `sample_docs/` has two tiny files; the demo script's "11 PDFs" are git-ignored, so a clone gives an empty library and a thin report. | [R] | A small open-access demo corpus (6-10 arXiv papers, licences checked) or `scripts/fetch_demo_corpus.py`; commit one finished sample report |
| A6 | **Dashboard `NEXT_PUBLIC_API_URL` defaults to `http://localhost:3001/api`** while the server binds 127.0.0.1: opening the app at `127.0.0.1:3001` makes every streaming page fail ("Failed to fetch"). | [R] deep/page.tsx:59 | Derive the URL from `window.location.origin` at runtime |
| A7 | **`next build` needs internet** (`next/font/google`), so the Docker build fails offline, contradicting "fully local". | [R] layout.tsx | Use local or system fonts |
| A8 | Stale or personal docs in the repo (`next-steps.md` mentions "your two real goals", the 30 Sep audit says "56 uncommitted changes... CI would fail", plan and review notes). No `.gitattributes`, CONTRIBUTING, CHANGELOG. | [R] | Move working notes to `docs/history/`, add the files |

### B. Correctness bugs in the newest code (they break demoed features)
| # | Finding | Evidence | Fix |
|---|---|---|---|
| B1 | **Stop is lost at node boundaries.** `tracked` calls `step()` which sets status back to "running", overwriting "stopped"; the next node never sees the stop. My test only stops inside a node, so it cannot catch this. | **[V]** my runlog.py/goal_graph.py code; [R] | In `tracked`, check `is_stopped()` before `step()` and raise; `step`/`finish` must not overwrite "stopped" |
| B2 | **`RunStopped` is swallowed** by `except Exception` in `check_coverage` and `discover`: the run continues to the approval pause after Stop. | **[V]** | Re-raise `RunStopped`/`GraphBubbleUp` before those handlers |
| B3 | **Run record race (two writers).** Python and the dashboard both read-modify-write `.runs/<id>.json`; the lock is in-process only; an unreadable file (Windows sharing violation) resets goal, events and settings; a failed `os.replace` is swallowed so a run can show "running" forever. Dashboard "Stop requested" is shown even if the cancel failed. | [R] runlog.py:21-67, runs.ts:187-221 | Keep the stop request in its own file (`<id>.stop`) so the status file has one writer; distinguish "missing" from "unreadable"; retry the replace; unique temp names |
| B4 | **Global mutable state** (`STOP`, `LLM_STATS`) is shared by all runs and never cleared; concurrent runs would stop or miscount each other. | [R] deep_report.py:141, goal_graph.py:152 | Per-run context (`contextvars`), cleared in `finally` |
| B5 | **A dead Ollama passes plan, coverage and discover silently** (calls return "", the user sees "nothing in the library" for every question); health is checked only in `research`. | [R] | Check health after each LLM-heavy node; the doctor preflight (A4) catches most of it |
| B6 | **Labels can overstate.** A cited sentence with a number that is in none of its cited facts is labelled `[established]`; sentence splitting breaks on `. [E3]`, `."`, `1.`, "U.S.", code fences. | **[V]** logic in report_checks.py; [R] | Compare numbers against the cited evidence; fix the splitter; add tests; reword the label ("cited"), and the Limitations line ("every prose sentence of 4+ words") |
| B7 | Source id collisions drop distinct pages; seed URLs eat the source budget before user-picked sources; old-style arXiv ids (`hep-th/9901001`) crash PDF conversion; "gaps" silently becomes "all" when coverage is empty. | [R] collector.py:90, goal_graph.py:335,398, fetcher.py:45 | Hash into ids, picked sources first, slugify filenames, log or skip |
| B8 | **/deep shows "Collecting sources..." forever** after Stop or a silent failure, and the form stays locked; the SDK's `stop()` may not cancel server-side. | [R] deep/page.tsx:176-177 | Show "stopped or ended" with a link to the run; also POST `/api/runs/{id}/stop` |
| B9 | Possible SSE buffering by Next's gzip in `next start`; `data:` URLs pass into hrefs; resume inputs cleared before the call succeeds; polling a 404 forever. | [R] [U] | `no-transform`, a shared `safeHref`, clear on success, stop on 404 |

### C. Quality and honesty (what the README must not claim yet)
1. **The quality gate has no real validation.** Exit tests in `report-quality-plan.md` (gap report on an out-of-coverage goal, contradiction/uncited-number checks, 30-fact on-topic sample) are not run. The live run that was to test it was damaged by memory starvation.
2. **Overclaims to soften:** "Every claim is checked twice" (the second check is a small-model judgement that treats a missing `on_topic` as true); "every sentence is labelled" (not tables, headings, short sentences); EVALS.md says differences come "from the model, not sampling" because temperature is 0 (Ollama is not bit-deterministic); "fully local, no API keys" (the collector, DuckDuckGo and Docling's first download use the internet; LangSmith tracing uploads runs if a key is set).
3. Thresholds are defined in three places and disagree (3 facts in report_checks and config, "fewer than 2" in the Limitations text).
4. Test suite is wide but leans on mocks of the exact functions that matter (plan, coverage, evidence); no test for stop-between-nodes, concurrent writers, a dead Ollama in the early nodes, or the labeller edge cases.
5. The faithfulness labels (8 contestable) are still unverified by a human; the judge accuracy number must stay "preliminary".

### D. Hygiene positives (verified by the reviewer, [R])
No secrets, personal paths or large files are tracked (`git grep` for keys, `C:\Users`, emails: clean); `.env`, vault data, reports and logs are ignored; commit emails are noreply. Remaining: a live LangSmith key sits in the ignored `dashboard/.env.local` and was printed in tool output earlier in this session: **rotate it**.

## 4. Quality assessment as a senior AI engineer
- **Strong:** fail-closed verification (verbatim quote + judge), honest limits, measured choices (hybrid vs BM25 vs dense; writer model by benchmark), SSRF-aware collector, resumable runs, run observability, audits and decision records, real bugs found by running it, not only by reading.
- **Weak:** the newest layer (gate, labels, stop, run records) was written fast and tested mostly with mocks; Windows file semantics were not considered; global state; duplicated collectors (`fetcher.collect` vs `collector.collect_selected`); config sprawl; `print` instead of logging.
- **Risk to credibility:** a reviewer who runs the gate on a real, uncovered goal will judge the project on that one run. It must be validated before it is shown.

## 5. Plan to close in 3 days

### Day 1: make it run, fast, and stop lying (about 6 hours)
1. Memory: free the machine (your OK needed for the 15 GB 28-Sep python job; Docker Desktop is mine to close), baseline one timed question, preflight warning, explicit model unload (`model-memory-plan.md` tasks 1-5).
2. B1-B5: Stop between nodes, RunStopped re-raise, single-writer stop file and safe run record, per-run context for STOP/stats, health checks after early nodes, with tests that fail first.
3. B6: label correctness and splitter, with tests from the reviewer's cases.
4. A1: `langgraph-cli[inmem]` in the extra, lock regenerated, **re-verified in a fresh clone**.

### Day 2: packaging, the demo path, validation (about 6 hours)
5. A2-A5, A7-A8: README rewrite, `scripts/doctor.py`, Makefile (`setup`, `doctor`, `models`, `dev`, `test`, `demo`), demo corpus plus one committed sample report, Docker writer default, doc cleanup, `.gitattributes`, CONTRIBUTING, CHANGELOG.
6. A6, B8, B9 dashboard fixes, then **your browser click-through**.
7. **Validation run:** the saved small-model goal with collect-for-gaps, and one out-of-coverage goal that must produce a gap report with no recommendation. Record the exit-test results in EVALS.md, good or bad.
8. Deliverable-aware planning (stage 6) only if time remains; otherwise cut and say so in the README's limits.

### Day 3: finish and record (about 4 hours)
9. One round of fixes from day 2, CI (version matrix, `langgraph dev` plus `/ok` smoke, compose build), final audit: tests, lint, fresh-clone install, Docker up, one full live run.
10. **Demo video** (script below), README links, tag `v1.0`.

### Cut line
Disagreement detection, recursive crawling, `collect.py --web`, deliverable-aware planning (if late), Ollama-in-compose profile, auto-tuned thresholds, consolidating the two collectors (list it as known debt).

## 6. Packaging target

### Quick start the README should have (bare metal)
```
git clone <repo> && cd 04-local-deep-research-vertical
make models        # ollama pull llama3.1:8b gemma4:e4b qwen3-embedding:0.6b  (about 12 GB)
make setup         # python 3.11 venv, pip install -e ".[dev]", npm ci, copies .env files, asks for VAULT_PATH
make doctor        # checks Ollama, models, paths, ports, free RAM; prints the fix for anything missing
make dev           # backend on 2025 and dashboard on 3001
# open http://localhost:3001 -> Deep Research -> pick the demo goal
```
Docker path: `make models`, `docker compose up --build`, open :3001. Windows without make: `scripts/setup.ps1` and `scripts/dev.ps1`.
README top section: one-paragraph pitch, screenshot/GIF, a diagram of both graphs, honest limits, link to the committed sample report.

### Demo video (3 minutes, scripted and reproducible)
0:00 problem and promise (30 s) -> 0:30 start a goal on the demo corpus; answer the two clarifying questions (30 s) -> 1:00 the **coverage card**
showing answered/thin/nothing and choosing "collect for gaps" (30 s) -> 1:30 the review list with PDFs and web pages separate; tick a few (30 s) ->
2:00 the Runs page progress, then jump to the **pre-run finished report** (the real run takes 10-15 min, so record it earlier) (30 s) -> 2:30 the report:
status table, a gap note, labelled sentences, grouped sources (30 s). Record on Docker for a reproducible environment; pin the model tags in the description.

## 7. Open decisions for you
1. The 15 GB python job from 28 Sep (PID 45288): leave it or stop it? Docker Desktop: may I close it?
2. Python version to support (I suggest 3.11 and 3.12 only).
3. Demo corpus: arXiv RAG papers (I suggest 6-8, open access) so the demo is about this project's own subject.
4. If day 2 runs long, cut stage 6 (deliverable-aware planning)? I suggest yes.
