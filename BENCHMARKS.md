# Model benchmarks

Three model-selection decisions in this project were made by measuring against
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

## 2. Debate mode's CPU-pinned critic

`scripts/benchmarks/benchmark_debate_critic.py` - debate mode pins a second,
smaller model fully to CPU (`num_gpu=0`) so it can run concurrently with the
GPU-resident advocate. Speed matters here specifically because the critic
must not become the slower half of that concurrent pair.

| Model | Time | Notes |
|---|---|---|
| **gemma3:4b** (chosen) | 15.3s | Sharp, specific critique; different model family from the advocate |
| llama3.2:3b | 12.7s | Fastest, also good quality - but same family (Meta) as the default advocate |
| qwen3.5:2b | **255.0s** | Disqualifying - ~20x slower despite being the smallest model |

`llama3.2:3b` was initially picked for speed, then deliberately swapped for
`gemma3:4b` (Google) once we realized `llama3.2:3b` is the *same model
family* as the default advocate (`llama3.1:8b`, Meta) - same-family models
share training data and alignment, producing a much weaker, more agreeable
"debate" than two genuinely different models. The ~20% speed cost was worth
it for a real second opinion. `qwen3.5:2b`'s catastrophic slowness matches
the same anomaly seen with `qwen3.5:4b` in benchmark 1 - the `qwen3.5` family
appears to have some CPU-inference inefficiency independent of model size.

## 3. Comparison mode's multi-tool-calling reliability

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
