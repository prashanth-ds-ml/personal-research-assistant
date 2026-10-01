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
