# Next steps for project 4 (written 2026-10-01, end of session)

State: audit fixes are implemented and committed (offline tests 181 passing, lint clean). Library migrated (80 docs
at the time; 98 after your last run's auto-ingest). Docker acceptance passed. v6 RAG run: 66 facts, 12 sources, no
empty sections (see EVALS.md). Services: dashboard 3001, backend 2025, both on 127.0.0.1 only.

## Do next, in this order
1. **Fix the runaway-generation hang** (see DECISIONS.md, "A streaming model call can never time out"). Output cap,
   per-call wall clock, repeat detector, per-question checkpoint inside `research`, test with a never-stopping fake
   model. This blocks real use: a real goal hung for 1.5 h.
2. **Re-run your saved goals.** The text and your answers are in `logs/saved-goals-2026-10-01.md` (the backend was
   restarted, so the paused threads are gone). Watch the first long run for stuck calls.
3. **Build the web collector** exactly as in `docs/web-collector-design.md` (module and tests first, then the graph
   pause and dashboard card, then a live run). The user called it the last piece for this project.
4. **Project 6** needs the collector for its evidence base (see `06-srh-health-assistant/docs/design.md`).

## User-owned
- Browser click-through of `/deep` and `/new` (leave mid-run and come back, stop button, feedback).
- Check the 8 contestable faithfulness labels (ids 2, 9, 11, 16, 25, 31, 34, 39 in `evals/faithfulness_sheet.csv`).
- Rotate the LangSmith key in `.env` if anyone else can see the session transcript (it was printed once).

## Known, not blocking
Plan revision can reshuffle unrelated sections; the failure-modes section in v6 is thin; Turbopack tracing warning;
quick assistant `config_schema` deprecation warning; four GPT-3 appendix chunks above 3,500 characters.
