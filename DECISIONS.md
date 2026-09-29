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

While adding debate mode's per-run checkbox, it silently had no effect no
matter what the dashboard sent. Root cause: `Configuration.from_runnable_config`
reads `os.environ.get(NAME, configurable.get(name))` - an environment
variable, once set, wins over *any* per-run override, forever, with no
error or warning. `.env` had `MAX_WEB_RESEARCH_LOOPS=3` and
`ENABLE_DEBATE_MODE=False` set from early in the project - meaning **the
dashboard's "max research loops" input had never actually worked**, since
long before debate mode existed. It surfaced now only because debate mode's
default (`False`) happened to match what silent failure looked like, whereas
the loop-count field silently *always being 3* was invisible because 3 was
also a reasonable-looking value. Fixed by removing both from `.env` and
documenting the precedence rule directly next to where it bites (see
`Configuration.from_runnable_config`'s docstring and `.env.example`'s
comments). The lesson: a config precedence rule that's correct but
undocumented at the point of use is a bug waiting to be found by whichever
feature happens to make its effect visible.

## Two models on one small GPU, without them fighting

Debate mode needs two different models' opinions without doubling wall-clock
time. The card here has 8GB VRAM with another process holding ~6GB of it -
not enough room for two full models loaded simultaneously on GPU. The fix:
`ChatOllama(..., num_gpu=0)` forces a model fully onto CPU (system RAM
instead of VRAM), so a GPU-resident model and a CPU-resident model don't
contend for the same memory pool and can run via `asyncio.gather` as genuine
concurrent requests rather than one queued behind the other. Verified with
`ollama ps` mid-run showing one model at `100% GPU` and the other at
`100% CPU` simultaneously - not inferred, observed. Measured ~3.4x faster
than the same two calls run sequentially (11.4s vs. 38.5s wall-clock for a
matched pair). The same `asyncio.to_thread` pattern (a different concurrency
primitive, for a different reason - genuinely independent long-running work,
not a memory-pool split) is what makes comparison mode's parallel entity
research work without touching any of the existing, tested single-topic
node code.

## Same-family models make a weak debate

Debate mode's first working version paired `llama3.1:8b` (the default GPU
model) with `llama3.2:3b` on CPU - both Meta/Llama, same training data and
alignment lineage, just different sizes. That's not a debate, it's the same
model arguing with a smaller version of itself. Swapped the CPU critic to
`gemma3:4b` (Google) instead - a different lab, different training data,
genuinely more likely to disagree. Confirmed qualitatively: the Gemma critic
engaged with specific numbers in a report ("the 10-30 million invocations
crossover point... lacks any rigorous analysis of the type of invocation")
rather than generic hedging, a noticeably sharper critique than the same-
family pairing produced. Cost: ~20% slower CPU inference (`gemma3:4b` vs.
`llama3.2:3b`) - worth it for a debate that's actually a debate.

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
