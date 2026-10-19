# LangChain / LangGraph: what to use for scope v2 / v2.1

Reviewed 2026-10-12 against the current docs (docs.langchain.com) and the
installed versions: langchain 1.4.2, langchain-core 1.6.4, langgraph 1.2.12,
langchain-ollama 1.1.0, langgraph-cli 0.4.32. `langgraph-checkpoint-sqlite`
3.1.1 (not yet a dependency) was inspected directly.

**Today the research graph uses only `StateGraph` + `interrupt`.** Retries,
stop, run records, per-run options and JSON parsing are hand-written. Several
open bugs (globals, options lost on resume, retries vs timeouts) map onto
built-in features.

Principle: **keep the research pipeline an explicit graph** (bounded,
checked steps); **use an agent only for chat** (open-ended conversation).
Adopt a framework feature only where it removes our own code or a known bug.

---

## 1. Research pipeline (Phase 1): LangGraph Graph API

| Feature | API | Use for | Scope items / bugs |
|---|---|---|---|
| **Send (map-reduce)** | `from langgraph.types import Send`; conditional edge returns `[Send("read_question", {...}) for q in questions]`; results via `Annotated[list, operator.add]` | One isolated reading task per question; checkpointed per task, so a resume skips finished questions (pending writes kept) | P1.2, isolation |
| **Subgraph** | compiled graph added as a node | "Read one question" = retrieve → extract → verify → subject check → select, testable on its own | P1.8, P1.9, P1.11 |
| **defer=True** | `builder.add_node("select", fn, defer=True)` | Selection waits until all question branches finish | P1.11 |
| **max_concurrency** | config `{"max_concurrency": 1}` | One model call at a time on one GPU (Send still gives structure + resume) | memory safety |
| **RetryPolicy** | `from langgraph.types import RetryPolicy`; `add_node(..., retry_policy=RetryPolicy(max_attempts=3, retry_on=...))` | Replace hand-written retries; `retry_on` = connection errors only, **not** timeouts (keeps DECISIONS rule) | P1.19 |
| **CachePolicy + SqliteCache** | `from langgraph.types import CachePolicy`; `compile(cache=...)` (`langgraph.cache.memory.InMemoryCache`; SqliteCache exists, path to confirm) | Cache extraction/verification per (passage hash, question, model, prompt version): re-runs, resumes, model tests and Phase 3 reuse skip repeated hours | P1.10, P3.2 |
| **Runtime context** | `StateGraph(State, context_schema=RunOptions)`; node `runtime: Runtime[RunOptions]` | Per-run options (limits, collection, models) without globals or state pollution | P1.19 (per-run state), options-lost-on-resume |
| **Command** | `Command(update=..., goto="revise")` | Critique → revise loop with a round counter; routing after checks | P1.13 |
| **interrupt** | already used | Clarify, plan + collection-rule approval, optional exclude list (v2.1 replaces source ticking) | P1.18 (built) |
| **Durability** | `durability="sync"` on stream/invoke | Multi-hour runs: persist before each step | reliability |
| **Time travel / fork** | `get_state_history(config)`; invoke with `checkpoint_id`; `update_state(..., as_node=...)` | **Model test**: fork one saved run at the writing step and run each candidate model on identical evidence; re-write a report with new limits without re-reading | section 9, P1.1 |
| **Custom streaming** | `from langgraph.config import get_stream_writer`; `writer({...})`; `stream_mode="custom"` (also `tasks`) | Live progress to the dashboard from inside nodes; run record keeps one writer | P1.19 (run record two writers) |
| **Encrypted checkpoints** | `EncryptedSerializer.from_pycryptodome_aes()` (`LANGGRAPH_AES_KEY`) | Optional; useful for client demos with sensitive libraries | later |

Note: under `langgraph dev` the server manages the checkpointer
(`.langgraph_api/`). Standalone runs and tests use
`langgraph.checkpoint.sqlite.SqliteSaver` (package
`langgraph-checkpoint-sqlite`).

### Model calls

| Feature | Use for | Note |
|---|---|---|
| `ChatOllama.with_structured_output(Schema, method="json_schema")` | Fact extraction into the structured fact model (core + AI/ML fields); critique output; decision steps | Today: plain `format="json"` + manual parsing. Schema-constrained output removes a class of parse failures. **Verify with gemma4:26b in the model test** (the structured-output doc does not list Ollama explicitly; langchain-ollama supports schema `format`) |
| Thinking on/off per call (`reasoning` option in langchain-ollama) | Thinking only for the decision step | Verify parameter name on 1.1.0 |
| One `num_ctx` (32k) for every research call | Model loads once | Changing `num_ctx` reloads the model |

---

## 2. Chat with the library (Phase 2): LangChain v1 agent + middleware

`from langchain.agents import create_agent`, tools as `@tool` functions,
fast chat model, `SqliteSaver` checkpointer, one thread per chat (P2.7).

**Tools:** `search_passages(query, collection)`, `search_facts(query,
filters)`, `open_source(source_id)`, `collection_coverage(collection)`,
`start_report(goal, collection)`.

**Built-in middleware (`langchain.agents.middleware`):**

| Middleware | Use for |
|---|---|
| `HumanInTheLoopMiddleware(interrupt_on={"start_report": ...})` | Confirm before starting a multi-hour report (P2.6) |
| `ModelCallLimitMiddleware(run_limit=...)`, `ToolCallLimitMiddleware(...)` | Runaway-loop guard per turn |
| `ContextEditingMiddleware()` (`ClearToolUsesEdit`) | Drop old retrieved passages so a small context stays usable |
| `SummarizationMiddleware(model=..., trigger=..., keep=...)` | Long conversations on a small context |
| `ToolErrorMiddleware`, `ModelRetryMiddleware` | Tool failures become messages; transient Ollama errors retried |
| **Custom middleware** (`after_model` hook) | **Our rules in code**: every claim cited, every number found in a retrieved passage/fact, coverage statement present; otherwise one rewrite request, then a safe reply (P2.3-P2.5) |

Not needed: `LLMToolSelectorMiddleware` (5 tools), `ProviderToolSearchMiddleware`
(Anthropic/OpenAI only), shell/filesystem middleware.

**Agentic RAG pattern** (docs tutorial): grade retrieved passages for
relevance (structured yes/no), rewrite the query and retry once when they
miss, then answer. Use it inside `search_passages`, or as a middleware step,
so thin retrieval leads to a rewrite or an honest "the library doesn't cover
this", not a weak answer.

**Streaming:** `stream_mode="messages"` for tokens in the chat UI.

**Report hand-off:** `start_report` creates a run of the `deep_research`
graph through the LangGraph SDK (already served by `langgraph dev`), seeded
with the chat's goal and collection.

---

## 3. Library, fact bank, memory (Phases 1-3)

| Need | Recommendation | Why |
|---|---|---|
| Passage search (hybrid FTS5 + vectors, namespaces) | **Keep our own `knowledge.py`** | Works, tested, has BM25 + vectors; LangGraph stores have no keyword search |
| **Fact bank** (structured fields, joins to sources/passages, tiers, dedupe, filters like `stage = 'fine-tuning'`) | **Own SQLite tables** in the same DB as the library | Needs SQL filters, joins and provenance; a key-value store is the wrong shape |
| Chat memory across threads (user preferences, "currently researching X") | `langgraph.store.sqlite.SqliteStore` (sqlite-vec semantic search, TTL), via `runtime.store` | Local, built-in, cross-thread; embeddings from Ollama (`nomic-embed-text` / `qwen3-embedding`) via `index={"embed": ..., "dims": ..., "fields": [...]}` |

---

## 4. Evaluation

| Tool | Use for | Local? |
|---|---|---|
| `agentevals.create_trajectory_match_evaluator` (modes strict/unordered/subset/superset; tool-argument matching) | Chat: did the agent call the right tools with the right arguments? Deterministic, no LLM | Yes; plain pytest asserts |
| `agentevals.create_trajectory_llm_as_judge` | Chat answer quality | Judge model is configurable; check a local Ollama judge works |
| pytest + saved runs (forked checkpoints) | Report checks: subjects, number provenance, labels, overlap | Yes |
| LangSmith (`@traceable`, `client.evaluate`) | Experiment history | **Cloud.** Off by default for the local-only/privacy story; optional for development |

---

## 5. Deliberately not adopted

| Option | Why not |
|---|---|
| **Deep Agents** (`create_deep_agent`) for the research pipeline | An open-ended plan/subagent loop is the opposite of our bounded, checked steps, and small local models are weakest at free agent loops. We already have what we would take from it: context isolation per question and offloading to disk. `RubricMiddleware` (beta) is the same idea as our critique → revise, which we build as explicit nodes |
| langgraph-bigtool | Chat has ~5 tools |
| LangChain vector stores replacing `knowledge.py` | Would lose keyword search and namespaces; no gain |
| Functional API | Graph API fits; one style across the codebase |

---

## 6. Dependency changes this implies

- Add `langgraph-checkpoint-sqlite` (SqliteSaver for tests/chat, SqliteStore, SqliteCache if that is where it lives).
- Add `agentevals` to the dev extra (Phase 2).
- No other new packages.
