# Next steps for project 4 (updated 2026-10-01)

State: deep research, the web collector, the Runs and Reports pages and the stop/progress machinery are built,
tested offline (228 tests, lint clean) and live-tested. Services: dashboard 3001, backend 2025, both on 127.0.0.1 only.
Your two real goals ("MY GOAL ..." and the long "ROLE ..." goal) are listed on the Runs page; the first is waiting
for you, the second was stopped. The goal texts are also in `logs/saved-goals-2026-10-01.md`.

## To do
1. **Use it on your real goals** (open Runs -> a waiting run -> *Open to answer*, or start the goal again). Use
   *Find and collect new sources first* and, for health or legal topics, set `COLLECT_ALLOW_DOMAINS`.
2. **Browser click-through** of `/runs`, `/runs/<id>`, `/deep` (review card, Stop), `/` (Deep/Quick tabs).
   Everything was checked through the API and type-checked, not clicked in a browser.
3. **Small gaps in the collector:** `scripts/collect.py --web` (papers only today); allow-list presets for health
   and law; recursive crawling inside one trusted site (design section 11).
4. **Plan quality:** section titles still come from the model, and revision requests can reshuffle unrelated sections.
5. **Project 6** can now start its evidence base with the collector (see `06-srh-health-assistant/docs/design.md`).

## User-owned
- Check the 8 contestable faithfulness labels (ids 2, 9, 11, 16, 25, 31, 34, 39 in `evals/faithfulness_sheet.csv`).
- Rotate the LangSmith key in `.env` if anyone else can see the session transcript (it was printed once).

## Known, not blocking
A thread that was busy when the backend was killed stays marked busy in LangGraph (a ghost; the Runs page shows its
record as stopped). Turbopack tracing warning; quick assistant `config_schema` deprecation warning; four GPT-3
appendix chunks above 3,500 characters; some sites (for example Databricks) answer 403 to automated fetches and are
skipped and recorded in the manifest.
