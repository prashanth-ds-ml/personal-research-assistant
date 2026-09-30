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
