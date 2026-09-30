# Model benchmarks

Two model-selection decisions in this project were made by measuring against
the actual prompts this graph uses, not by assumption. Scripts live in
`scripts/benchmarks/` and are runnable against your own local Ollama models -
these results are from one machine (RTX 5050, 8GB VRAM, another process
holding ~6GB of it) and will vary on different hardware, but the *method* -
test the real prompt shape, test a positive and a negative case, don't trust
a library's own claims - is the point.

## 1. Chat model (`LOCAL_LLM`)

`scripts/benchmarks/benchmark_chat_models.py` - JSON-mode query generation and
unconstrained summarization, the two prompt shapes this graph relies on most.

| Model | Query-gen | Summarize | Total | Valid |
|---|---|---|---|---|
| **llama3.1:8b** (chosen) | 10.5s | 9.6s | **20.1s** | yes |
| granite4.1:8b | 10.2s | 15.3s | 25.5s | yes |
| qwen3:8b | 16.4s | 14.5s | 30.9s | yes |
| ministral-3:8b | 13.8s | 19.9s | 33.7s | yes |
| deepseek-r1:8b (tutorial's suggested model) | 21.9s | 15.0s | 36.9s | yes |
| qwen3.5:latest | 18.7s | 25.5s | 44.2s | yes |
| qwen3.5:4b (original default) | 41.4s | 26.7s | 68.1s | yes |

All seven produced valid, non-empty output - this was purely a speed decision.
`llama3.1:8b` was ~3.4x faster than the model it replaced, with no quality
tradeoff on spot-check. Notably the tutorial's own suggested model
(`deepseek-r1:8b`) wasn't the fastest despite being an R1-style "thinking"
model this repo's `strip_thinking_tokens` machinery was clearly built around.

## 2. Comparison mode's multi-tool-calling reliability

`scripts/benchmarks/benchmark_tool_calling.py` - comparison mode's
`plan_research` node depends on a model reliably calling one tool multiple
times in a single turn when it detects a comparison, and exactly once when it
doesn't. This needed empirical validation, not assumption - the risk (per
`open_deep_research`'s own docs) is that small local models are less
reliable at multi-parallel-tool-calls than frontier cloud models.

| Model | Positive case (want 3 calls) | Negative case (want 1 call) |
|---|---|---|
| **llama3.1:8b** (chosen, no swap needed) | 8.7s, 3/3 correct | 1/1 correct |
| llama3.2:3b | 7.5s, 3/3 correct | 1/1 correct |
| ministral-3:8b | 12.2s, 3/3 correct | - |
| granite4.1:8b | 10.1s, 3/3 correct | - |
| qwen3.5:latest | 17.0s, 3/3 correct | - |
| lfm2.5:8b | 14.2s, 3/3 correct | - |
| qwen3:8b | 14.6s, **2/3** (under-called) | - |
| qwen2.5-coder:7b | 20.5s, **0/3** (failed entirely) | - |

Positive case: "Compare PostgreSQL vs. MongoDB vs. Redis for a high-write-
throughput analytics workload." Negative case: a plain single-topic question,
to confirm the model discriminates rather than habitually over-splitting.
`llama3.1:8b` (the existing default) handled both correctly and fastest, so
no model swap was needed for comparison mode - a real risk turned out not to
apply to this specific model, which is exactly why it was worth testing
instead of assuming.

## 3. Deep-research model roles

`scripts/run_deep_report.py` with each model in all three roles (planner,
extractor, writer) on the same goal and library, before the retrieval fixes
(v2 pipeline; the qwen3 run finished, a second attempt crashed on an Ollama
`/tokenize` connection error, so its numbers are from the first run).

| model | run time | verified facts | cited facts | empty sections | papers used | verdict |
|---|---|---|---|---|---|---|
| llama3.1:8b | ~9 min | 56 | 45 | 0 | 6/11 | fastest, most stable extractor |
| qwen3:8b | ~3-4 min per question (vs ~1 for llama) | n/a | 46 | 0 | 7/11 | most on-topic prose, several times slower, cites ranges like `[E6-E9]` |
| gemma4:e4b | 12.5 min | 35 | 31 | 2 | 5/11 | best prose and tables, but extracts fewer facts |
| granite4.1:8b | 8 min | 18 | 16 | 2 | 5/11 | weakest: few facts, uncited tables |

Conclusion drawn from measurement: **extract with llama, write with gemma.**
With the v5 pipeline, that mix produced ~21% more body text (2,619 vs 2,165
words) at the same number of cited facts, for about 8% more time
(12.0 vs 11.1 minutes). qwen3's slowness and the tokenizer crash ruled it out
as a default despite good prose. Note the caveat: one goal, one run per cell;
planner variance is large enough that small differences (5-10%) are within noise.
