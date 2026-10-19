# Build order: sprints and test gates

Scope: `SCOPE.md` v2.2. Each sprint is small enough to finish and test on its
own. Phase docs (`docs/phases/`) hold the full task and test lists; this file
says **in which order**, **who tests what**, and **what must pass** before
moving on.

**Who:** 🧑 you · 🤖 Claude · 🤝 both. Durations are rough estimates.

## Testing rule: test everything possible

- **🤖 Claude tests** everything that can be automated or scripted: unit,
  integration, golden (saved evidence), adversarial, budget, performance, live
  model runs on Ollama, API calls against the running backend and dashboard,
  dashboard end-to-end checks with Playwright (headless, screenshots), lint,
  type check, secret scan, fresh-clone install. Claude also labels evals
  independently so your labels have a second opinion.
- **🧑 You test** what needs a person: blind quality scoring, labelling, real
  daily use, how the UI feels, your machine (RAM, power), your accounts (keys),
  decisions, fresh-eyes reading. Listed with status in `docs/USER_TESTS.md`.
- Your tests marked **blocking** must pass before the sprint gate. The others
  run in parallel and feed the next sprint.

## Every sprint ends the same way

1. 🤖 Sprint tests pass → full offline suite green (`pytest`, dashboard `npm test`, `tsc`, lint)
2. 🤖 Live checks for the sprint (model run, API, Playwright) where relevant
3. 🧑 Blocking user tests done (`USER_TESTS.md`)
4. 🤖 Review (`REVIEW_CHECKLIST.md`); every failure → `ERROR_LOG.md` → fix → regression test
5. 🤖 Docs updated: `STATUS.md`, phase Results, `DECISIONS.md` (if a decision was made), `EVALS.md` scoreboard (at gates), **`CASE_STUDY.md` sprint log**
6. 🤖 Commit by topic (on your OK)

---

## Phase 1a-0: Measure first (no big model)

### Sprint 0: Housekeeping (½ day)
| | |
|---|---|
| Build 🤖 | Commit planning docs · review + commit the October code fixes separately · commit the dashboard snapshot · log `langchain-community` sunset and `config_schema` deprecation |
| Tests 🤖 | Full offline suite; dashboard tests + `tsc` (after clearing stale `.next` types); diff review of the October fixes against their tests |
| Tests 🧑 | U-01 read the code-fix review |
| **Gate** | Suite green; `git status` shows only intended leftovers |

### Sprint 1: Error analysis + eval set (2-3 days)
| | |
|---|---|
| Build 🤖 | ~50-claim labelling sheet from saved runs · `evals/subject_facts.jsonl` (~40 cases incl. E7/E8, E79, E76/E40) · judge calibration script |
| Tests 🤖 | P0-T01-T03; Claude labels the 50 claims independently; re-run `retrieval_qa.json` as baseline; judge vs your labels agreement |
| Tests 🧑 | U-02 label claims · U-P2 settle 8 disputed labels |
| **Gate** | Error breakdown by stage in `EVALS.md`; judge agreement known |

### Sprint 2: Dev loop, scoreboard, code audit (2 days)
| | |
|---|---|
| Build 🤖 | Mini fixture (< 10 min) · file-based writing replay · fact viewer · `scripts/scoreboard.py` (v6 column) · code-audit list; archive v1 quick mode if chosen |
| Tests 🤖 | P0-T04-T07; mini fixture timed live; if archived: full suite, dashboard build, Playwright smoke over remaining pages |
| Tests 🧑 | U-03 fact viewer readable · U-04 keep/archive decision |
| **Gate** | **P1a-0 exit gate**; 1b/1c order re-set from the error analysis (DECISIONS entry) |

## Phase 1a: Foundations + model test

### Sprint 3: Foundations (2-3 days, no big model)
| | |
|---|---|
| Build 🤖 | `langgraph-checkpoint-sqlite` · `RunOptions` via `context_schema` (E-004, deprecation) · checkpoint-fork harness · doctor v2 (RAM fit, v2 models, `OLLAMA_MAX_LOADED_MODELS=1`) |
| Tests 🤖 | P1a-T01, T02, T03, T07; two concurrent runs live on the mini fixture; fork replays writing only (call counts checked) |
| Tests 🧑 | none blocking (U-P3 memory routine in parallel) |
| **Gate** | No shared state between runs; fork replays writing only |

### Sprint 4: Model test (3-4 days, mostly machine time)
| | |
|---|---|
| Build 🤖 | Confirm candidate tags; pull (~60 GB) · baseline evidence from the saved SLM goal · runs 1-6 · run 7 raw-passage baseline · run 8 critique on/off · blind report packs |
| Tests 🤖 | P1a-T04 (JSON-schema output, thinking on/off, SqliteCache), T05 (fit, paging, minutes per step), T08; Claude's own blind scores |
| Tests 🧑 | U-05 free RAM · **U-06 blind-score reports** · U-07 read the winner |
| **Gate** | **P1a exit gate**: model decided; raw-passage + critique results on the scoreboard; L10 measured |

## Phase 1b: Collecting, reading, chat preview

> Sprints 5 and 6 may swap: the stage with the most errors in Sprint 1 goes first.

### Sprint 5: Collect wide + library structure (3-4 days)
| | |
|---|---|
| Build 🤖 | Collections · tiers · version merge + dedupe · collect wide (rules approval, exclude list, L2 cap, index all) · source states + origin · ranking · E-002 |
| Tests 🤖 | P1b-T05, T06, T12-T19; one live wide run (counts vs index); Playwright: Library shows states/origin |
| Tests 🧑 | **U-08 real wide collection** · U-09 spot-check 10 sources |
| **Gate** | A wide run indexes everything; counts match; collections isolated |

### Sprint 6: Structured facts + fact bank (4-5 days)
| | |
|---|---|
| Build 🤖 | Reading subgraph per question (Send) · structured extraction · subject check by fields · fact bank + provenance · CachePolicy · RetryPolicy |
| Tests 🤖 | P1b-T01-T04, T07-T11; subject eval set score vs raw-passage baseline; crash-and-resume live |
| Tests 🧑 | **U-10 hand-check 30 facts** |
| **Gate** | 0 subject violations in 30; beats the raw-passage baseline on subject accuracy |

### Sprint 7: Chat preview (2 days build + 1 week use, overlapping Sprint 8)
| | |
|---|---|
| Build 🤖 | Chat over passages + fact bank: cited, checked vs unchecked, refuses when nothing found · minimal page |
| Tests 🤖 | P1b-T20, T21; 10 scripted questions live; Playwright: ask → answer → source link opens |
| Tests 🧑 | **U-11 daily use for a week** · U-12 try to break it |
| **Gate** | **P1b exit gate**; scoreboard column "P1b" |

## Phase 1c: Writing + claim check view

### Sprint 8: Writing (4-5 days)
| | |
|---|---|
| Build 🤖 | Report types · options → questions + decision · selection ≤ 80 · decision step · critique → revise (only if S4 showed it pays) · summary from decision · provenance + label rules · budgets logged |
| Tests 🤖 | P1c-T01-T11, T14; full live run on gold goal T1; budget log check |
| Tests 🧑 | **U-13 read a full report** |
| **Gate** | E-001 closed; beats raw-passage baseline on numbers, labels, blind score |

### Sprint 9: Claim check view (2-3 days)
| | |
|---|---|
| Build 🤖 | Reader: claim → fact → passage with highlighted quote; label and number provenance |
| Tests 🤖 | P1c-T12; Playwright clicks every claim in the sample report and checks the quote is highlighted |
| Tests 🧑 | **U-14 click 20 claims** |
| **Gate** | **P1c exit gate**; scoreboard column "P1c" |

## Phase 1d: Hardening + v1.0 release

### Sprint 10: Hardening (3-4 days)
| | |
|---|---|
| Build 🤖 | E-003, E-005, E-006, E-007 · `durability="sync"` · dashboard: collections, limits, states, counts; deploy redesign · CI |
| Tests 🤖 | P1d-T01-T04, T08; kill-Ollama and Stop/resume live; Playwright full-page smoke; CI run |
| Tests 🧑 | **U-15 dashboard click-through** · **U-16 failure handling from the UI** |
| **Gate** | E-003..E-007 closed; CI green |

### Sprint 11: Release + portfolio (3-4 days)
| | |
|---|---|
| Build 🤖 | README hero + diagram · `make` + Windows scripts · demo corpus · sample report · evals page · **CASE_STUDY final form** · notes → `docs/history/` · remove personal content |
| Tests 🤖 | P1d-T06 fresh clone in a temp folder, T09 secret scan over full history; Claude's blind scores on 3 gold goals |
| Tests 🧑 | **U-P1 rotate key** · **U-17 repo visibility** · **U-18 blind-score gold goals** · **U-19 fresh-eyes README** · **U-20 demo video** |
| **Gate** | **v1.0**: tag, public release, demo video |

---

## After v1.0 (sprints planned in detail at each phase start, same testing rule)

| Phase | Sprints | Gate |
|---|---|---|
| 2 Chat | 12 chat-model test + model swap · 13 agent, tools, citation middleware, threads · 14 chat page, "make this a report", demo video | P2 acceptance (SCOPE section 8) |
| 3 Compounding | 15 reports from the library, fact reuse · 16 freshness, contradictions, collection health | P3 acceptance |
| 4 Domains + demo | 17 domain-pack format + second domain (client type decided first) · 18 demo corpus, offline demo script, client one-pager | P4 acceptance |

## Critical path

Sprint 0 → 1 → 2 → 3 → **4 (needs ≥ 12 GB free RAM)** → 5/6 → 7 → 8 → 9 → 10 → 11.
Sprints 0-3 need no big model. Your blocking inputs: U-01 (S0), U-02 + U-P2 (S1), U-04 (S2), U-05 + U-06 (S4), U-08 (S5), U-10 (S6), U-11 (S7), U-13 (S8), U-14 (S9), U-15 + U-16 (S10), U-P1 + U-17-U-20 (S11).
