# Engineering decisions and debugging notes

Non-obvious problems hit while building this, how they were diagnosed, and
why the fix was the fix. Kept separate from the README so the main docs stay
a reference, not a diary — but this is the part worth reading if you want to
know how the thing was actually built, not just what it does.

## "It ran once and looked fine" is not evidence

Every model/config decision in this project was made by running the actual
prompt shape the graph uses against multiple candidates and measuring, not
by reading a benchmark leaderboard or trusting a library's own claims. Full
methodology and results in [BENCHMARKS.md](BENCHMARKS.md). The short version:
the tutorial's suggested model wasn't the fastest, the original default model
was the *slowest* of seven candidates despite being one of the smaller ones,
and a plausible-sounding risk (small local models can't reliably multi-tool-
call) turned out not to apply to the specific model already in use — findings
that would have been invisible without actually testing.

## The search backend was silently broken, not just "sometimes fails"

`duckduckgo_search` (the library this is forked with) returned an empty
result set for every query at one point, with no exception raised - the
pipeline degraded gracefully (an empty research loop, not a crash), which
made it easy to mistake for normal rate-limiting rather than a real
regression. Confirmed by calling the library directly, in isolation, outside
the graph entirely: `ddgs.text(query)` returned `[]` regardless of query
content. Checking the installed package's own metadata revealed it had been
renamed upstream to `ddgs` months earlier, with the old name kept only as a
compatibility shim. Switching the import fixed it completely - verified with
a real run that went from 0 archived sources to 6-12 genuinely relevant ones.
The lesson: when something that used to work stops working, check whether
the dependency itself changed before assuming the calling code is wrong.

## A stuck port cost more debugging time than it should have

Mid-session, `langgraph dev` on port 2024 started returning stale data from
a process that had already been killed - confirmed by `Get-NetTCPConnection`
and `Get-CimInstance` showing a listener with no resolvable owning process.
Multiple `taskkill`/`Stop-Process` attempts didn't clear it. The actual fix
was mundane (move to port 2025), but the diagnostic path mattered: `ps aux`
(MSYS-space PIDs, from the shell environment) and `tasklist`/`netstat` (real
Windows PIDs) were reporting *different numbers for the same process*,
which made "is this actually dead" genuinely ambiguous until cross-checked
against the authoritative Win32 API (`Get-NetTCPConnection`) rather than
either shell's own view. Worth knowing before spending time debugging a
`langgraph dev` instance that seems to be running old code: check what's
actually bound to the port, not just what your terminal launched.

## A dormant bug was found while building something unrelated

While adding a per-run checkbox to the dashboard, it silently had no effect no
matter what the dashboard sent. Root cause: `Configuration.from_runnable_config`
read `os.environ.get(NAME, configurable.get(name))` - an environment
variable, once set, wins over *any* per-run override, forever, with no
error or warning. `.env` had `MAX_WEB_RESEARCH_LOOPS=3` set from early in the
project - meaning **the dashboard's "max research loops" input had never
actually worked**. It surfaced only because the new checkbox's silent failure
was visible, whereas the loop-count field silently *always being 3* was
invisible because 3 was also a reasonable-looking value. Fixed by removing it
from `.env` and documenting the precedence rule directly next to where it bites
(see `Configuration.from_runnable_config`'s docstring and `.env.example`'s
comments). It has since been tightened further: an empty variable counts as unset, and a per-run
`configurable` may only set the few keys in `PER_RUN_KEYS` (paths, URLs and model names come from
the environment only). The lesson: a config precedence rule that's correct but
undocumented at the point of use is a bug waiting to be found by whichever
feature happens to make its effect visible.

## Comparison mode runs its entities concurrently

Comparison mode researches each entity independently and at the same time,
using `asyncio.to_thread` around the existing, tested single-topic node code.
The work is genuinely independent and long-running, so a thread per entity
makes the parallel research work without touching any of that existing code.

## Why comparison mode doesn't copy `open_deep_research`'s architecture

[`open_deep_research`](https://github.com/langchain-ai/open_deep_research)
(LangChain's own deep-research agent, ranked on the Deep Research Bench
leaderboard) does comparisons via a supervisor LLM that decides to call a
research tool N times in one turn, purely through prompt instructions - no
code branches on "is this a comparison." That mechanism was worth borrowing;
its control flow (a full ReAct supervisor loop with dynamic tool-call-driven
fan-out) wasn't, for one concrete reason: it depends on a model reliably
emitting *multiple* tool calls in a single turn, which is a materially
different reliability bar than the single-tool-call structured outputs this
project already leaned on elsewhere. Rather than assume that would work with
a local 8B model, it was benchmarked directly (see `BENCHMARKS.md` #3) -
`llama3.1:8b` handled it perfectly, but two other candidates didn't (one
under-called, one failed entirely), confirming the risk was real *in
general* even though it happened not to apply to the model already in use.
Comparison mode was built as a much narrower version - one planning node,
one tool, one decision (how many sub-topics) - specifically to keep the
surface area that depends on multi-tool-calling reliability as small as
possible, rather than adopting a general-purpose supervisor loop that would
depend on it repeatedly, across many more decisions, over a run.

---

# Deep research mode: decisions and bugs

## Small models need small jobs
An 8B model asked to "research X and write a report" in one context produces
confident mush. The pipeline instead splits work into steps a small model does
well: one JSON planning call; many tiny (passage, question) -> facts calls;
deterministic verification; one writing call per section that sees only that
section's evidence. The first end-to-end run showed why each guard exists: the
planner invented a premise ("local vs large models") the goal never stated, and
a benchmark table attributed GPT-3's scores to "local language models".

## The faithfulness judge was broken by my own prompt
The first judge prompt demanded that the *quote* name the claim's subject, while
the extraction prompt (correctly) asked for claims to name their subject
explicitly. Contradictory rules made the judge reject everything: a full run
produced 0 evidence and an empty report. Diagnosed by calling the judge directly
on a known-good claim and a known-bad one. Fix: show the judge the whole passage
(so "RAG models" can come from context) and ask for a one-sentence reason before
the verdict. After the fix it passed good claims and caught the wrong-subject
case with a correct reason. Lesson: a verifier needs its own test on a positive
and a negative case, or it can fail silently in the safe direction.

## Retrieval failures hide as writing failures
The section "how do LLMs learn from examples" kept being wrong even after the
planner and judge were fixed. The cause was upstream: the vague question
retrieved GraphRAG's evaluation criteria and reference lists, never the few-shot
paper. Three fixes, each measured: multi-query expansion plus a cap of 3
passages per paper (papers used 6 -> 10 of 11), a HyDE query (a hypothetical
answer in the papers' own vocabulary), and dropping reference/acknowledgement
chunks (959 -> 820 chunks, retrieval unchanged). Reading the *retrieved
passages*, not the report, is what found it.

## Recommendations cannot be retrieved
A "Practical recommendations" section had no evidence because no paper says what
this team should do. Rather than let the model invent advice, the planner marks
the last section as synthesis and it is written from the other sections'
findings, allowed to cite only ids those sections cited. Limit found afterwards:
it can still merge two true findings into a false composite claim; no per-claim
check catches that.

## One flaky generation must not kill a two-hour run
A run died at minute ~10 with Ollama's "prediction aborted, token repeat limit
reached". Now every call goes through a retry wrapper that raises temperature and
repeat penalty on each attempt (which is what breaks degenerate loops), and, if
all attempts fail, returns an empty string that the pipeline already treats as
"no facts" / "section failed". Also recorded per run (`llm_retries`,
`llm_gave_up`) so degradation is visible, not silent.

## Incremental ingest must skip *before* the slow step
Docling takes 1-4 minutes per PDF. The first ingest script converted every file
and only then noticed the content was unchanged, so "incremental" re-did all the
work. Change detection now hashes the source file's bytes and skips before
conversion (7 unchanged files: 0 seconds instead of ~15 minutes).

## Measure, don't guess, about model roles
Four local models, one goal: llama3.1:8b was fastest and the best extractor;
gemma4:e4b wrote the best prose but extracted fewer facts; granite4.1:8b was
weakest; qwen3:8b was slow and crashed once. Result: a mixed setup (llama
extracts, gemma writes) that costs about 8% more time for about 21% more text.
Details in BENCHMARKS.md.

## Things that went wrong in the environment
- A Windows file lock stopped a `mv`; another process held the PDFs open. Copied,
  verified byte-identical, and deleted the originals only after the lock cleared.
- Long background jobs were killed by the OS under memory pressure. Runs are
  now sequential, unload each model from Ollama before the next, and abort if
  free memory drops below 3 GB.
- Compose reads `./.env` for `${...}` substitution, which silently injected the
  host's `OLLAMA_BASE_URL` into containers; only `DOCKER_*`-prefixed names are
  substituted now.

---

# M0: making it usable (2026-09-30)

## Adding a second folder would have silently deleted the first
`ingest_folder` pruned every indexed document whose file was not found under
the folder being ingested. Fine with one folder; the moment the vault's sources
were added, running the ingest for either folder would have wiped the other.
Caught by reading the prune loop before adding the second folder, not by a
failure. Fix: every folder is a namespace (`library/...`, `Sources/...`) and
pruning only touches its own namespace; a test ingests two folders, deletes a
file from one, and checks the other is untouched.

## Which vault folders become evidence
Only `Sources/` (archived web pages) is indexed, not `Research/`. The Research
notes are reports a model wrote earlier; using them as evidence would make the
assistant cite its own earlier output, which amplifies any error it made then.
(The quick assistant still reads them as *context*, a different and intended use.)

## The graph and the scripts disagreed about where the library lives
The graph read `<vault>/.kb/library.sqlite`; the library had been built into a
file in the project folder. A run from the dashboard would have opened an empty
library and written "no supporting evidence" in every section - and my offline
tests could not have shown it, because they inject fakes. One function
(`knowledge.default_kb_path`, honoring `KB_PATH`) is now used by the graph and
every script.

## OCR was most of the ingest time and did nothing for our PDFs
Docling runs OCR by default. On one born-digital paper: 77 s with OCR, 21 s
without, output identical (same characters, same table rows). OCR is now off,
with an automatic second pass with OCR when a PDF yields almost no text for its
page count (scans). Both branches are tested with fake converters.

## The autostart script could never have started the backend
`start-research-assistant.ps1` looked for `langgraph.exe` in a per-project
`.venv` that does not exist (the repo uses one shared venv). It would have
started the dashboard and silently not the backend at the next login. It now
falls back to the shared venv and writes an error to the startup log instead of
starting nothing.

## Planning broke when the goal carried clarification text
Walking the flow through the dashboard's API showed the revised plan had lost
the recommendations section and used raw questions as section titles. Cause:
with long clarification text in the goal, the model sometimes returns sub-
questions but no `outline` key; at temperature 0 that repeats exactly, and the
fallback (one section per question) also dropped the synthesis section. Fix: a
second, focused call that only groups the given questions into sections, and a
fallback that still ends with the synthesis section. Reproduced with the exact
failing prompt before and after.

## Distractor documents cost a little precision at the top ranks
Adding the vault's 66 archived web pages to the 11 papers (77 documents, 2,465
chunks) moved hybrid recall@1 from 80% to 76% and recall@3 from 92% to 88%;
recall@6 stayed at 96%. BM25 and dense alone fell further at some cutoffs. The
practical reading: keep retrieving 6-8 passages per question, which the
pipeline already does.

## The web collector is one agent, and we write our own fetching
(Decided 2026-10-01; design in `docs/web-collector-design.md`; not built yet.)

Deep research could read the library but not *find* web pages. Options weighed: (a) a separate search graph,
(b) a search-backend component plus a separate fetch component, (c) one collector module.
Chosen: **one independent module, `collector.py`**, with search as a pluggable function inside it
(DuckDuckGo via `ddgs` by default, SearXNG if configured, no paid APIs). The deep-research graph and
`scripts/collect.py` both call it, so it works standalone from the command line. Two calls, `discover`
(search, dedupe, triage; downloads nothing) and `collect` (fetch, convert to markdown, save), with a review pause
between them so the user sees every candidate and approves the list. Fetching is strictly sequential.

**LangChain's web loaders were not adopted.** `WebBaseLoader`, `RecursiveUrlLoader` and friends are thin wrappers
over requests and BeautifulSoup. They have none of what this project needs (public-host-only checks with redirect
re-validation, robots.txt, per-host rate limits, size caps, manifest, dedupe), so adopting them would mean wrapping
them in our own guards and adding dependencies for little saved work. Extraction already uses `trafilatura`
(better main-content and table extraction than generic HTML-to-text) and PDFs use Docling. Only crawling inside a
single trusted site might be worth revisiting later, built on our own fetcher. (This comparison is from memory of
the loaders' design; re-check the current versions before citing it.)

**Why the review pause:** general web search returns SEO pages. The relevance score pre-ticks the good ones, and
the user's ticking is the real quality filter. An optional domain allow-list (WHO, CDC, NHS, government sites)
covers high-stakes topics. The pause can be switched off for unattended runs.

## A streaming model call can never time out, so one bad call hung a whole run
(Found 2026-10-01 from a real run; **fixed the same day**, see the end of this entry.)

LangSmith showed a deep-research run as "incomplete". The cause was not LangSmith: the run had sat for about
1.5 hours inside one model call in the `research` step. Ollama's log showed a single request that had generated
about 79,000 tokens at 53 tokens/s with repeated context shifts (8,192-token window): the model never emitted a
stop token. Our `LLM_TIMEOUT = 300` is an HTTP read timeout; a streaming response resets it on every token, so a
model that keeps talking is never timed out. There was also no cap on output length, and the step saves its
evidence only when it finishes, so cancelling lost all of the run's work. Cancelling the run in LangGraph marked it
interrupted, but the blocked worker thread kept the connection open, so Ollama kept generating until the backend was
restarted (in-memory threads were lost; the goals were saved to `logs/saved-goals-2026-10-01.md`).

Planned fix, in this order:
1. Cap output length (`num_predict`) on every call, sized per task (extraction and judging are short).
2. A wall-clock limit per call, not just a per-chunk read timeout.
3. A repeat detector: stop a call whose output loops, then let the existing retry run at a different temperature.
4. Checkpoint progress inside `research` (per question) so a failure at question 4 keeps questions 1-3.
5. A test with a fake model that never stops, and the stuck-call case added to the walkthrough checks.
Likely trigger (an inference, not confirmed): JSON mode on a small model looping on whitespace or repeated text.

## Model choice for a private deployment is a study inside project 6, not a new tool
(Decided 2026-10-01.) A separate "model-fit" tool was considered and researched. The space is already covered:
quality evals by promptfoo, Inspect (UK AISI), DeepEval, lm-evaluation-harness and MedHELM; load and latency by
GuideLLM (performance only, no quality, no cost); capacity and cost by calculators such as tokcalc (formula-based).
"Runs inside the customer's environment" is therefore not a differentiator. No single tool was found that joins
measured quality, measured speed and cost into one recommendation, but the search was limited. Decision: do not build
a new eval engine; run a model-selection study inside project 6 with the existing tools and publish one report.

### Fix, and what the fix turned up (2026-10-01)
- Model calls now stream through `consume()`, which stops one that repeats itself (any 1-200 character unit repeated
  for 80+ characters), passes a character cap, runs past 240 s, or after Stop; output is also capped with `num_predict`
  (1,200 tokens for JSON, 2,500 for prose). A stopped or runaway call is retried (runaway) or ends the run (stop).
- Every run writes a record to `<vault>/.runs/<thread id>.json` (`runlog.py`): step, counters, activity log, outcome.
  The dashboard's Runs page and live view read it, and also ask the backend whether the thread still exists, so a
  record that says "running" is shown as stopped, lost or possibly stuck when it is not. Evidence is also saved after
  every question, and a retry resumes after the last finished one.
- **Stop is cooperative.** Cancelling a LangGraph run does not interrupt a node that is running in a worker thread: it
  keeps going (and kept the GPU busy) until the step ends. The dashboard's Stop now also writes `stopped` into the
  run record; every model call and the streaming loop check it, so a run stops within a few seconds (measured: 21 s
  to a fully idle Ollama).
- **Per-run options were being lost.** The dashboard sends `collect_sources` and `seed_urls` only with the call that
  starts a run; each resume after a pause carries no config, so those settings silently reverted to their defaults and
  the "fetch new sources" checkbox did nothing since it was added. Found because the new discover step finished
  instantly with no search. They are now stored in the run's state when it starts (`options`) and read from there.
- **Threads survive a backend restart.** `langgraph dev` saves its state to `.langgraph_api/` and restores it, so
  paused runs were not lost when the backend was restarted (an earlier note here and in the session said they were:
  wrong). What persisted is invisible on the Runs page unless a record exists, so `scripts/backfill_runs.py` creates
  records for threads that predate run records. A thread that was busy when its server was killed stays marked busy
  (a ghost); the record for it says stopped.
- **A plan always ends with a recommendations section.** It used to exist only if the model left its last section with
  no questions; otherwise the report had no recommendations. `make_plan` now appends one when the model did not.
- **Feedback that steers is not a topic.** "Keep it focused on X" and "make it shorter" were turned into a new
  section and a research question. Such notes (keep, make, stay, be, use, prefer, avoid, shorten, lengthen,
  simplify) are now passed to the planner and not enforced as sections.

## A time limit meant to catch runaways killed healthy writes on a slow machine
(2026-10-01) A real chunking run produced a report in which all four evidence sections read "The model failed to write this section",
while the status table said "supported" and the summary was a model-written paragraph about having nothing to summarise. Cause: the
240 s per-call limit (added to stop endless generations) also killed slow but healthy section writes; each section took 12 minutes
(3 retries of 240 s) on a GPU running at 180 MHz. Fixes: prose calls get 1,200 s and the loop and length checks are the real guard; a
timed-out call is not retried; a section the model failed to write is marked "failed" (not "supported"), and when half or more failed the
summary is written by code and says to free memory and run again; the facts of failed sections go to the appendix; placeholder notes
are not labelled as claims. Lesson: a guard tuned on a healthy machine must degrade gracefully on a slow one, and a gate must look at
what was actually written, not only at what evidence existed.

## The slowdown was mostly a power-capped GPU, not memory
(2026-10-01) Measured: per-question time 33-235 s on healthy runs against 316-1,483 s on a slow one; committed memory 76 GB on 23.6 GB RAM
(a 3-day-old 15 GB python job, Docker Desktop's VM 7.6 GB that I had started and not closed, a WebView2 app); gemma4:e4b keeps 5.4 GB of
weights in system RAM (all 43 layers on the GPU). After closing Docker (free RAM 2.4 -> 4.6 GB) the baseline was still 5-10x slow:
the GPU runs at 180 MHz (max 3,090) with a 10 W power ceiling (default 80 W), reason "software power cap", while charging at 3.6 W.
Decision: memory hygiene and a preflight check stay in the plan, but speed is judged only after the power cap is fixed; the model
scheduler is demoted to cheap insurance.

## Coverage check validated on an out-of-coverage goal
(2026-10-01) Goal: "How does reciprocal rank fusion combine rankings?" The coverage check marked all 7 questions "nothing". A direct
search of the library confirmed it: "reciprocal rank fusion" appears in 2 chunks of 1 blog page, in passing, with no explanation. So the
check refused correctly instead of letting the report fill with off-topic material (the failure of the original small-model report).

## Scope v2: narrow, quality first, chat and a compounding library (2026-10-12)
Context: the v1 scope (3 Oct) was never locked. Discussion on 12 Oct changed the direction. The model's context, not the number of
collected documents, bounds a report: the decision step only ever saw ~24 compressed sentences however many PDFs were collected, and
compression at each step is where the subject and stitching errors came from. Decisions (full text in `docs/SCOPE.md`):
- **Quality over speed.** CPU offload and multi-hour runs are acceptable.
- **One research model that reasons and writes:** `gemma4:26b-a4b` (qat, ~16 GB, MoE ~4B active), 32k context for every research call
  (one setting, so it loads once). Chosen from the Ollama "tools + thinking" list by fit (8 GB GPU + 24 GB RAM) and family (gemma4:e4b
  wrote the best prose in BENCHMARKS). To be confirmed by a model test on identical saved evidence (Phase 1a), against qwen3:30b-a3b,
  gemma4:12b, qwen3.5:9b, a qwen3.5:27b ceiling check and the v6 mix. Rejected: "maximum context" (32k is the realistic ceiling on this
  machine, and 8B-class models do not reason evenly across long prompts); nemotron-3-nano:30b and qwen3.5:35b (too big for RAM).
- **The selected evidence must fit in one context.** Limits: 3-4 questions, ≤12 sources read per question, ≤50 per run, ≤4 facts per
  source, ≤80 facts in the writing step, library unlimited; everything left out is listed.
- **Structured facts** (core + AI/ML pack fields) so the subject check compares fields; **fact bank** stored for reuse.
- **Draft → critique → revise**; number provenance and labels enforced in code.
- **Two report types** (decision brief, state of the evidence); 1,500-3,000 words.
- **Chat with the library** (Phase 2): fast model, cited, coverage statements, refuses general-knowledge answers, hands off to reports.
  Rejected framing: "works without the internet forever" (libraries go stale; freshness is shown instead).
- **"Any domain"** only via domain packs, proven with a second domain in Phase 4; AI/ML first.
- **Framework use** (`docs/FRAMEWORK_FIT.md`): Send + subgraph per question, RetryPolicy, CachePolicy, runtime context, Command,
  checkpoint fork for the model test, custom streaming; `create_agent` + middleware for chat; own SQLite for passages and the fact bank;
  SqliteStore for chat memory. Not adopted: Deep Agents for research, bigtool, replacing `knowledge.py`; LangSmith off by default.
- **Process:** phases with tests first, review, error log and gates (`docs/PROCESS.md`); Phase 1 split into 1a-1d.

## Scope v2.1: collect wide, index everything, chat preview early (2026-10-18)
Context: the user pointed out that a run may find hundreds of sources but only a few can be used; the rest should go into the
knowledge base, and a growing knowledge base should be chattable (RAG). The tool must be useful to the user first, then become a
private-first deep research product to demo to clients. Decisions (full text in `docs/SCOPE.md` section 5):
- **Four levels per run:** found → collected + indexed (no LLM, all of them) → read (≤50, fact bank) → used (≤80 facts). The collection
  bound is a safety cap (~300), not the context. Collected sources were already auto-indexed; the change is discovery and choice.
- **No ticking:** the user approves the plan and collection rules; the candidate list stays as an optional exclude list.
  Rejected: ticking ~100 candidates (does not scale to hundreds).
- **Source states** `indexed` / `read` / `used` and **origin** `web` / `upload` stored per source; chat says checked vs unchecked.
- **Chat preview at the end of Phase 1b**, used daily before Phase 2 is designed in detail. Rejected: full chat before Phase 1 (without
  the fact bank it cannot tell checked facts from unchecked passages, the E-001 failure).
- **Product direction recorded; client work deferred.** Private sources for clients (intranets via connectors, exports or a signed-in
  crawler with permission; on-premise; per-user access filtering) are feasible but backlog until a client asks. Only `origin` is stored now.

## Scope v2.1 locked (2026-10-18)
The user asked to finalize the scope. `docs/SCOPE.md` v2.1 is locked with the section 12 defaults: limits as written (tuned after the
model test), one library with topic collections, 1,500-3,000-word reports, gemma4:e4b for the chat preview, ~300-source collection cap.
Second domain and first client type are deferred by design to Phase 4. Further scope changes need a DECISIONS entry and a version bump.
Next: Phase 1a (blocked only on free RAM: reboot before the model test).

## Scope v2.2: measure first, simplest baseline, claim check as the centrepiece (2026-10-19)
Context: a review through the lenses of Karpathy (look at the data, simple baselines, fast loops, human verification) and Ng (error
analysis, evals first, data-centric, decide what to work on). The v2.1 plan chose fixes by diagnosis, had only the v6 baseline, and a
3-5 h run as its only loop. Decisions (full text in `docs/SCOPE.md`, S10-S13):
- **Phase 1a-0 "Measure first"** before any Phase 1a code: ~50 claims labelled by first failing stage, eval set (subject facts,
  retrieval, faithfulness with the 8 disputed labels settled, calibrated judge), one scoreboard, mini fixture + writing replay, code audit.
- **Raw-passage baseline** (retrieve → raw passages in 32k → write with quotes) in the model test; every structured stage must beat it
  or is cut. **Critique on/off** measured; draft → critique → revise kept only if it raises the blind score.
- **Claim check view** (claim → fact → highlighted quote) moved from dashboard polish to Phase 1c.
- **Portfolio deliverables and pre-publish clean-up** are part of the Phase 1d gate; v1.0 is the public release.
- **Code audit:** v1 quick-research mode (~1,650 lines, the only user of `langchain-community`) is kept or archived by the user in Sprint 2.
- Build order in sprints with test gates: `docs/BUILD_ORDER.md`. Phase 1b/1c task order is re-set after the error analysis.

## Process: test everything possible, user-test list, living case study (2026-10-19)
The user asked that everything possible be tested, with the tests only they can do listed separately, and that a case study be
maintained alongside the other project docs. Process change, not a scope change (scope stays v2.2):
- Claude tests everything automatable: offline suites, live Ollama runs, API calls, dashboard end-to-end with Playwright (headless),
  secret scan, fresh-clone install, independent second labels on evals.
- `docs/USER_TESTS.md` lists the person-only tests (U-P1..P4 any time, U-01..U-20 per sprint) with status; blocking ones gate their sprint.
- `docs/CASE_STUDY.md` is a living document: a sprint-log entry every sprint, final form at v1.0 (Sprint 11).
- `BUILD_ORDER.md` now lists Claude's tests and the user's tests per sprint and a common end-of-sprint routine.

## Sprint 0 closed; branch per phase (2026-10-19)
The user reviewed the October fixes (U-01) and kept them; committed separately from the docs and the dashboard snapshot. Commits go on
one branch per phase (`phase-1a0` now), merged into `main` at each phase gate, so `main` always holds a passed gate. The review's
E-010 (prompt examples copied from the one test goal) adds a held-out gold goal to the Sprint 1 eval set.

## Scope v3: one engine, one model, feedback loop; research primary, chat secondary (2026-10-19)
Context: during Sprint 1 the user said the plan had become too complicated (50-claim labelling sheet, judge calibration,
12 sprints) and asked to revisit the idea from the start. Decisions (full text in `docs/SCOPE.md`):
- **Write from chunks, not extracted facts.** The writer reads retrieved chunks (with document title and heading) directly; the
  fact-extraction step and LLM judge are removed. Reason: E-001 lives in the paraphrase step (subject right in 22/42 v1 facts).
- **Retrieval engine:** existing hybrid (BM25 + vectors, RRF) plus a cross-encoder reranker (M3), measured before it is switched on.
- **One LLM, `qwen3.5:4b`** (user's choice): with extraction gone only plan/write/chat remain; one model avoids swapping on a
  memory-short machine and fits the 8 GB GPU with a 16k window.
- **Short, evidence-led reports** (~1,500-2,500 words, section per sub-question, summary only from section sentences) with code checks
  on numbers, model names and citations.
- **Feedback loop** on sources, sentences and whole answers, stored with the engine version; it replaces the labelling and judge
  calibration as the evaluation, and gives the case study before/after numbers from real use.
- **Deep research is primary; chat is secondary** (user). Chat offers research when the library cannot answer, so it does not drift
  into plain RAG.
- **Process:** milestones M1-M5 instead of sprints; v2.2 plan docs moved to `docs/archive/v2.2/` (nothing deleted). Daily use by the
  builder starts at M2. Sprint 1 tooling stays; its labelling tasks (U-02, U-P2) are dropped.

## Thinking when planning: a setting, default off (2026-10-19)
qwen3.5:4b thinks without end at temperature 0 (E-014); with Qwen's thinking settings (temperature 0.6, top_p 0.95, top_k 20)
a plan takes 76-93 s instead of 8 s, is of similar quality, and varies between runs. The user chose a setting, default off:
`PLAN_THINKING` / `plan_thinking` (per run), used only by the planning step ("thinker" role). Passage judging, writing and the
other small calls never think (it would turn a 4-minute report into an hour).

## Run trace and feedback in a separate desk database, built before the first real test (2026-10-19)
The user asked to track every step, source and chunk, and to save feedback properly, before testing. M2 was pulled forward.
- One SQLite file per vault, `<vault>/.desk/desk.sqlite`, NOT the library database (rebuilt on re-embedding; feedback must
  survive). One schema file (`desk_schema.sql`) applied by both writers: Python writes the trace, the dashboard writes feedback.
- The trace: runs (engine, model, settings, plan, outcome), steps (duration, ok/paused/failed/stopped), every model call (step,
  role, sizes, time), every retrieved chunk per question (chunk id, text hash, keyword and meaning ranks, fused score), every
  0-3 grade, evidence E-number -> chunk, what each section's writer was given, every report sentence (citations, flag).
- Feedback is append-only (latest per target wins, "cleared" withdraws), validated per target (chunk: relevant / not relevant /
  wrong subject; sentence: wrong + reason; report: helpful / not helpful, mirrored from the existing thumbs). Each row carries
  the run, engine and chunk identity, so ratings can be compared before/after an engine change and survive a library rebuild.
- The current run's trace travels in a context variable set per graph step, not a global (E-004 was a shared-global bug).
- Tracing never breaks a run: write errors are swallowed with one warning.

## Report checks tightened after the first real v3 report (2026-10-19)
Review of *Embedding Models...* against its 17 chunks: most claims matched, but (1) the writer cited neighbouring chunks of
the same paper (E8 for what E7 says), (2) an uncited speed-benchmark table appeared under "Training Methodology", (3) the
model-written summary stitched five claims into one sentence, (4) flags rendered at the start of the next sentence.
Decisions: citation repair by word coverage (move when another chunk of the section covers >= 0.5 and +0.25 more; flag
"wording not found" below 0.2, thresholds measured on that report); tables must cite every row with cited numbers or are
dropped; the summary is copied from section sentences; v3 flags go before the full stop. v2 label style unchanged.

## Report page layout: the source margin no longer stretches chapters (2026-10-19)
The user saw large blank areas. Cause: the margin's evidence cards were twice as tall as the text. The margin now sticks
beside the text and scrolls on its own; cards are compact. Page 10,958 -> 8,227 px on the embeddings report.

## Chunk size locked: 1,800 / 3,000, recorded in the library (2026-10-19)
The user asked to fix the chunk size so every future source is cut the same way. Test A (25 frozen questions, sizes 600 to
3,500, recall by rank and by equal reading budget) put 1,400-2,500 on one plateau and 600-1,000 clearly below at top-1, so
1,800 stays. The library now records `CHUNKER = "v2 text=1800 table=3000"` and refuses to open for new documents with
other settings (like the embedding model). Two chunker bugs were fixed inside v2 before locking: a giant table header
pushed every piece over the limit (7,159 chars), and a broken 2,190-character PDF heading was prefixed to its chunks (now
capped at 300). The library was re-chunked once (165 documents, 5,099 chunks, all within limits; retrieval unchanged
80/88/96%). Embedding now goes in batches of 32 with retries.

## Section budget: the best 8 passages, best first; no neighbour expansion (2026-10-20)
Tests C and B (EVALS "v3 Tests B and C"). The 4B writer stays accurate up to ~5k tokens of sources, but a 150-300-word
section only uses ~8 passages and drops late ones (last third used 25% at 16 passages). So each section gets its 8
best-graded passages, best first (equal grades keep retrieval order); the rest is recorded in the run trace as not given
(`passages_not_given` in the run stats), never silently. Expanding chunks with their neighbours doubled the input without
improving use or drift, so it is not adopted. Thinking when writing looked clearly better on 4 writes but costs ~10x the
time per section; that choice is the user's.

## "Think when writing" is a setting, default off (2026-10-20)
The user chose a setting after Tests B/C (thinking cited 88% vs 80% of passages, used late passages too, left nothing
uncited, ~90 s vs ~9 s per section, 4 writes). `WRITE_THINKING` / `write_thinking` turns thinking on for the section writer
only, with Qwen's thinking sampling; both thinking options are toggles on the dashboard Settings page, whose defaults now
show the v3 setup (one model qwen3.5:4b, writer blank, 2 passages per section).

## Defaults after the full test: reranker on, thinking when writing on, sections 400-600 words (2026-10-20)
The user's choices after the three-run long-report test. Reranker (bge-reranker-v2-m3, CPU) on: offline top-3 88% -> 100%,
~15 s per question. Think when writing on: 92% clean sentences and no flags vs 77-86% without, +~7 min per report.
Section length 400-600 words (the user asked for the best): Test D found it as accurate as 150-300 with more passages used,
and padding only from ~800. Engine version v3.1-rerank. Tests use a fake reranker (tests/conftest.py) so they never load the
2 GB model. Planner fixed (E-019) before the final check run.

## Sources: papers and AI-engineering docs first; arXiv queried properly (2026-10-20)
The end-to-end audit found 15 of 16 report sources were web/blog guides. The user's primary domain is technical material on
LLMs, AI engineering, FDE, agents and LangChain. Decisions: an authority class per source (paper 3; official docs and the
AI-engineering expert sites 2; other web 1) breaks ties after relevance in candidate ranking and section passage order; an
unattended run also takes papers and docs one grade below the relevance bar. arXiv was queried with every word of the
question including fillers ("Which", "are", "available") and returned 0 papers for all six questions of the RAG goal; the
query now uses content words only and is limited to the AI/ML categories (setting `arxiv_categories`, default cs.CL, cs.AI,
cs.LG, cs.IR, cs.SE, cs.MA); the same six questions now find 4-5 papers each. Also: the relevance grade is bound to the
component the question names; restated sentences are dropped; the v3 status table says Passages; table passages display as
plain cells.

## Domain-specific sources stay, but the report must say the domain (2026-10-20)
The verification collection brought medical papers (via Europe PMC) into an AI-engineering goal. The user wants them kept:
other domains' LLM work is worth learning from. The risk is generalising a domain's result. Decisions: Europe PMC stays on;
the writer must name the domain of a domain-specific passage ("In a clinical decision-support study, ..."); code flags a
cited sentence whose source title names a domain (medical, legal, financial, biology, education) when the sentence does not
("check domain", v3 only).
