# Phase 2: Chat with the library

**Goal:** ask questions of a collection in conversation and get cited,
coverage-aware answers in seconds; hand off to a report when needed.

**Depends on:** v1.0 (P1d gate). Builds on the Phase 1b chat preview and the problems found using it (listed below).
**Scope items:** P2.1-P2.8. Framework: LangChain v1 `create_agent` + middleware (FRAMEWORK_FIT section 2).

## Inputs from the chat preview

_Filled in from daily use after the P1b gate._

## Tasks

- [ ] Chat-model test (qwen3.5:9b, gemma4:12b qat, gemma4:e4b) on a 30-question set: tool use, citation rate, latency; decision recorded.
- [ ] Model swap: unload the research model before chat (and back), with a visible "loading model" state.
- [ ] Tools: `search_passages`, `search_facts`, `open_source`, `collection_coverage`, `start_report`.
- [ ] Agentic RAG step: grade retrieved passages; rewrite query and retry once on a miss; else "not in your library".
- [ ] Middleware: HumanInTheLoop on `start_report`; ModelCallLimit + ToolCallLimit; ContextEditing; Summarization; ToolError + ModelRetry.
- [ ] Custom `after_model` middleware: every claim cited, every number found in retrieved evidence, coverage statement present; one rewrite, then a safe reply.
- [ ] Threads per collection with `SqliteSaver`; follow-ups.
- [ ] `start_report` → `deep_research` run via the LangGraph SDK, collect off by default.
- [ ] Chat page (evidence side panel, same reader style); token streaming (`messages` mode).

## Test cases

| ID | Type | Case | Expected |
|---|---|---|---|
| P2-T01 | Benchmark | 30-question set over the demo collection | ≥ 90% fully cited; 0 uncited numbers |
| P2-T02 | Trajectory (agentevals, no LLM) | Lookup questions | Correct tool + arguments (subset/unordered match) |
| P2-T03 | Adversarial | Question outside the library | Refuses general-knowledge answer; offers collect/research |
| P2-T04 | Unit | Answer with a number not in retrieved evidence | Blocked by middleware; rewritten or safe reply |
| P2-T05 | Unit | Every answer | Contains coverage statement (N sources, newest date, gaps) |
| P2-T06 | Integration | "Make this a report" | Confirmation interrupt; run created with matching goal and collection |
| P2-T07 | Unit | 40-turn conversation | Context stays within budget (summarization/context editing) |
| P2-T08 | Performance | Answer latency after model loaded | < 20 s |
| P2-T09 | Unit | Runaway tool loop | Stopped by call limits with a clear message |
| P2-T10 | Integration | Chat during a running report | Clear message (model busy) or queued; no crash, no memory paging |

## Exit gate
- [ ] All test cases pass; SCOPE section 8 Phase 2 acceptance met.
- [ ] No open Critical/High errors. Demo video updated.

## Results
_Fill in at the gate._
