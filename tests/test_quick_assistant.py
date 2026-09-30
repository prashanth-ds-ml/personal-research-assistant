"""Smoke tests for the quick assistant (graph.py), which had no automated tests at all."""

import json
from types import SimpleNamespace

import pytest

from research_assistant import graph as quick
from research_assistant.configuration import Configuration
from research_assistant.state import SummaryState


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in Configuration.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


def test_the_graph_compiles_with_the_expected_nodes_and_nothing_else():
    nodes = set(quick.graph.get_graph().nodes) - {"__start__", "__end__"}
    assert nodes == {"load_profile", "retrieve_vault_context", "plan_research", "generate_query", "web_research",
                     "summarize_sources", "reflect_on_summary", "parallel_research", "finalize_summary",
                     "update_profile", "notify_complete"}


def test_max_research_loops_is_the_number_of_search_passes():
    def route(done, maximum):
        return quick.route_research(SummaryState(research_loop_count=done),
                                    {"configurable": {"max_web_research_loops": maximum}})
    assert route(1, 1) == "finalize_summary"        # one pass asked for, one pass done: stop (it used to run two)
    assert route(1, 3) == "web_research" and route(2, 3) == "web_research"
    assert route(3, 3) == "finalize_summary"         # three passes in total
    assert route(1, 0) == "finalize_summary"         # the first pass always happens; never a second


class FakeLLM:
    def __init__(self, content):
        self.content = content

    def invoke(self, messages):
        return SimpleNamespace(content=self.content)


def query_from(content, monkeypatch, **cfg):
    monkeypatch.setattr(quick, "get_llm", lambda c: FakeLLM(content))
    c = Configuration(**cfg)
    return quick.generate_search_query_with_structured_output(
        c, [], None, "FALLBACK", "query", "query", secondary_field="rationale")


def test_a_thinking_models_json_after_its_reasoning_is_used(monkeypatch):
    content = '<think>let me think about this</think>{"query": "bm25 vs dense retrieval", "rationale": "compare"}'
    out = query_from(content, monkeypatch)
    assert out["search_query"] == "bm25 vs dense retrieval" and out["rationale"] == "compare"


def test_unusable_model_output_falls_back_instead_of_crashing(monkeypatch):
    for bad in ('["a list"]', '"a string"', "null", "not json", "", '{"query": ""}', "<think>unclosed"):
        assert query_from(bad, monkeypatch)["search_query"] == "FALLBACK"


def test_the_profile_pasted_into_every_prompt_is_capped(monkeypatch):
    big = "## Standing Preferences\nPrefers concise answers.\n" + "\n".join(f"- session {i}: did research" for i in range(2000))
    monkeypatch.setattr(quick.vault, "read_profile", lambda *a: big)
    monkeypatch.setattr(quick.httpx, "get", lambda *a, **k: None)             # the Ollama reachability check
    out = quick.load_profile(SummaryState(research_topic="x"), {"configurable": {}})
    assert len(out["profile_content"]) < quick.PROFILE_MAX_CHARS + 200
    assert out["profile_content"].startswith("## Standing Preferences")      # the top (preferences, newest entries) is kept
    assert "older profile entries omitted" in out["profile_content"]
    small = "## Standing Preferences\nshort"
    monkeypatch.setattr(quick.vault, "read_profile", lambda *a: small)
    assert quick.load_profile(SummaryState(research_topic="x"), {"configurable": {}})["profile_content"] == small


def test_plan_research_uses_the_configured_provider(monkeypatch):
    used = []

    class Tool:
        def __init__(self, name):
            self.name = name

        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            used.append(self.name)
            return SimpleNamespace(tool_calls=[{"args": {"research_topic": "topic A"}}, {"args": {"research_topic": "topic B"}}])

    monkeypatch.setattr(quick, "ChatOllama", lambda **k: Tool("ollama"))
    monkeypatch.setattr(quick, "ChatLMStudio", lambda **k: Tool("lmstudio"))
    state = SummaryState(research_topic="A vs B")
    assert quick.plan_research(state, {"configurable": {}})["entity_topics"] == ["topic A", "topic B"]
    monkeypatch.setenv("LLM_PROVIDER", "lmstudio")
    quick.plan_research(state, {"configurable": {}})
    assert used == ["ollama", "lmstudio"]


def test_comparison_planning_can_be_switched_off_and_falls_back_to_the_topic(monkeypatch):
    cfg = {"configurable": {"enable_comparison_planning": False}}
    assert quick.plan_research(SummaryState(research_topic="just one"), cfg)["entity_topics"] == ["just one"]


def test_the_quick_assistant_no_longer_has_any_trace_of_the_removed_feature():
    source = open(quick.__file__, encoding="utf-8").read().lower()
    assert "debate" not in source and "advocate" not in source
    assert not {"enable_debate_mode", "debate_cpu_model"} & set(Configuration.model_fields)
    assert json.dumps(sorted(SummaryState.__dataclass_fields__)).lower().count("critic") == 0
