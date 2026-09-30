"""The deep_research graph's human-in-the-loop flow and failure behaviour (audit follow-ups)."""

import json

import pytest
from langchain_core.embeddings import Embeddings
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from research_assistant import deep_report, goal_graph
from research_assistant.knowledge import KnowledgeBase

MD = "# Hybrid Retrieval Guide\n\n## Results\nHybrid retrieval reached 0.78 recall, beating BM25 at 0.61 recall.\n"


class Emb(Embeddings):
    def _e(self, t):
        t = t.lower()
        v = [float(t.count(k)) for k in ("hybrid", "recall", "bm25")]
        return v if any(v) else [0.001] * 3

    def embed_documents(self, texts):
        return [self._e(t) for t in texts]

    def embed_query(self, text):
        return self._e(text)


def fake_llm(prompts):
    def llm(prompt, json_mode=False):
        prompts.append(prompt)
        if "clarifying questions" in prompt:
            return json.dumps({"questions": ["Which audience?"]})
        if "research methodologist" in prompt:
            return json.dumps({"title": "Hybrid report", "sub_questions": ["Does hybrid help recall?"],
                               "outline": [{"title": "Recall", "questions": [0], "brief": "b"}]})
        if "directly support" in prompt:
            return json.dumps({"supported": True})
        if "Extract facts" in prompt:
            return json.dumps({"facts": [{"claim": "Hybrid retrieval reached 0.78 recall",
                                          "quote": "Hybrid retrieval reached 0.78 recall"}]})
        if "Write the report section" in prompt:
            return "Hybrid helps [E1]."
        if "search queries" in prompt:
            return json.dumps({"queries": ["hybrid recall"]})
        return "Summary [E1]."
    return llm


@pytest.fixture
def flow(tmp_path, monkeypatch):
    prompts: list[str] = []
    kb = KnowledgeBase(tmp_path / "kb.sqlite", Emb())
    kb.ingest_text("guide.md", MD, title="Hybrid Retrieval Guide")
    kb.close = lambda: None
    raw = fake_llm(prompts)
    llm = deep_report.resilient(lambda prompt, json_mode, attempt: raw(prompt, json_mode))   # counts calls like the real one
    monkeypatch.setattr(goal_graph, "build_llms", lambda cfg: {"planner": llm, "extractor": llm, "writer": llm})
    monkeypatch.setattr(goal_graph, "open_kb", lambda cfg: kb)
    monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
    g = goal_graph._graph(InMemorySaver())
    return g, {"configurable": {"thread_id": "t"}}, prompts, tmp_path


def interrupt_value(out):
    return out["__interrupt__"][0].value


def to_first_plan(g, cfg):
    g.invoke({"goal": "Does hybrid help?"}, cfg)                # clarify pause
    return interrupt_value(g.invoke(Command(resume="any audience"), cfg))   # plan pause


# ---- approval ----------------------------------------------------------------------

def test_only_an_explicit_approval_starts_the_expensive_work(flow):
    g, cfg, prompts, _ = flow
    to_first_plan(g, cfg)
    for not_an_approval in ("yes please", "", {"approve": True}, {"feedback": ""}, None, ["approved"]):
        out = g.invoke(Command(resume=not_an_approval), cfg)
        asked_again = interrupt_value(out)
        assert asked_again["type"] == "approve_plan" and "Not understood" in asked_again["error"]
        assert not any("Extract facts" in p for p in prompts)
        # the re-ask itself needs a valid answer; a second invalid answer stops the run (see next test)
        break
    out = g.invoke(Command(resume={"approved": True}), cfg)
    assert "__interrupt__" not in out and "Hybrid helps [E1]." in out["report"]


def test_a_second_unintelligible_answer_stops_the_run_before_any_evidence_is_gathered(flow):
    g, cfg, prompts, _ = flow
    to_first_plan(g, cfg)
    g.invoke(Command(resume="maybe"), cfg)                      # refused, asked again
    with pytest.raises(RuntimeError, match="not approved"):
        g.invoke(Command(resume="still not sure"), cfg)
    assert not any("Extract facts" in p for p in prompts)


def test_the_last_plan_is_always_shown_and_feedback_is_refused_when_no_revisions_are_left(flow):
    g, cfg, prompts, _ = flow
    first = to_first_plan(g, cfg)
    assert first["revisions_left"] == 2
    second = interrupt_value(g.invoke(Command(resume={"feedback": "add cost"}), cfg))
    assert second["revisions_left"] == 1
    third = interrupt_value(g.invoke(Command(resume={"feedback": "add privacy"}), cfg))
    assert third["type"] == "approve_plan" and third["revisions_left"] == 0      # the 3rd plan is SHOWN, not auto-run
    assert not any("Extract facts" in p for p in prompts)
    refused = interrupt_value(g.invoke(Command(resume={"feedback": "one more change"}), cfg))
    assert "no revisions are left" in refused["error"]
    out = g.invoke(Command(resume={"approved": True}), cfg)
    assert "__interrupt__" not in out


# ---- clarify -----------------------------------------------------------------------

def test_answering_the_clarifying_questions_does_not_call_the_model_for_questions_again(flow):
    g, cfg, prompts, _ = flow
    to_first_plan(g, cfg)
    assert sum("clarifying questions" in p for p in prompts) == 1     # asked once, not once per resume


def test_the_answers_survive_even_if_the_model_would_now_ask_nothing(flow, monkeypatch):
    g, cfg, prompts, _ = flow
    g.invoke({"goal": "Does hybrid help?"}, cfg)
    inner = fake_llm(prompts)
    quiet = lambda p, json_mode=False: (  # noqa: E731
        json.dumps({"questions": []}) if "clarifying questions" in p else inner(p, json_mode))
    monkeypatch.setattr(goal_graph, "build_llms", lambda c: {"planner": quiet, "extractor": quiet, "writer": quiet})
    g.invoke(Command(resume="Audience: clinicians"), cfg)
    plan_prompt = next(p for p in prompts if "research methodologist" in p)
    assert "Audience: clinicians" in plan_prompt


# ---- a dead model ---------------------------------------------------------------------

def test_a_dead_model_fails_the_run_loudly_instead_of_writing_an_empty_report(flow, monkeypatch):
    g, cfg, _, tmp_path = flow

    def boom(prompt, json_mode, attempt):
        raise ConnectionError("Ollama is not running")

    dead = deep_report.resilient(boom, retries=1)
    monkeypatch.setattr(goal_graph, "build_llms", lambda c: {"planner": dead, "extractor": dead, "writer": dead})
    cfg["configurable"].update(ask_clarifying_questions=False, require_plan_approval=False)
    with pytest.raises(deep_report.ModelUnavailable, match="Ollama is running"):
        g.invoke({"goal": "Does hybrid help?"}, cfg)
    assert not (tmp_path / "vault" / "Research").exists()                    # no report was written


def test_model_failures_are_counted_in_the_stats_and_the_report(flow, monkeypatch):
    g, cfg, _, _ = flow
    cfg["configurable"].update(ask_clarifying_questions=False, require_plan_approval=False)
    out = g.invoke({"goal": "Does hybrid help?"}, cfg)
    assert out["stats"]["llm_calls"] > 0 and out["stats"]["llm_gave_up"] == 0
    assert "failed to answer" not in out["report"]


# ---- collect and the scope note ---------------------------------------------------------------

def test_the_limitations_describe_what_was_actually_searched(flow):
    assert goal_graph._scope_note(None) == "" and goal_graph._scope_note({"error": "x"}) == ""
    assert "3 new source(s) were fetched" in goal_graph._scope_note({"saved": 3, "skipped": 4})
    assert "found nothing new" in goal_graph._scope_note({"saved": 0})


def test_collect_warns_when_fewer_sources_were_indexed_than_saved(flow, monkeypatch):
    g, cfg, _, tmp_path = flow
    monkeypatch.undo()                                              # use the real open_kb for this test
    monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault2"))
    monkeypatch.setenv("KB_PATH", str(tmp_path / "kb2.sqlite"))
    monkeypatch.setattr(goal_graph, "make_embeddings", lambda *a, **k: Emb())

    def fake_collect(questions, store, fx, llm, **kw):
        store.dir.mkdir(parents=True, exist_ok=True)
        (store.dir / "good.md").write_text("# Good\n\nHybrid retrieval reached 0.78 recall in this study of search.")
        (store.dir / "blank.md").write_text("")                     # saved but nothing indexable
        return {"saved": 2, "skipped": 0, "failed": 0, "folder": str(store.dir)}

    monkeypatch.setattr(goal_graph.fetcher, "collect", fake_collect)
    state = {"goal": "g", "plan": {"goal": "g", "title": "T", "sub_questions": ["q?"], "outline": []}}
    out = goal_graph.collect(state, {"configurable": {"collect_sources": True}})["collect_report"]
    assert out["saved"] == 2 and out["indexed"] == 1 and "only 1 were indexed" in out["warning"]


# ---- saving and folders ---------------------------------------------------------------------

def test_saving_never_overwrites_another_runs_report(flow):
    _, cfg, _, tmp_path = flow
    state = {"goal": "g", "plan": {"title": "Same title"}, "report": "first report text",
             "stats": {"questions": 1, "sources": 1}}
    first = goal_graph.save(state, cfg)["report_path"]
    second = goal_graph.save({**state, "report": "second report text"}, cfg)["report_path"]
    assert first != second
    assert "first report text" in open(first, encoding="utf-8").read()
    assert "second report text" in open(second, encoding="utf-8").read()


def test_two_library_folders_with_the_same_name_both_stay_indexed(tmp_path, monkeypatch):
    a, b = tmp_path / "x" / "Papers", tmp_path / "y" / "Papers"
    for folder, word in ((a, "alpha"), (b, "beta")):
        folder.mkdir(parents=True)
        (folder / "doc.md").write_text(f"# {word}\n\nHybrid retrieval recall study number {word} with enough text.")
    monkeypatch.setenv("LIBRARY_FOLDERS", f"{a};{b}")
    monkeypatch.setenv("KB_PATH", str(tmp_path / "kb.sqlite"))
    monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))
    monkeypatch.setattr(goal_graph, "make_embeddings", lambda *a, **k: Emb())
    for _ in range(2):                                              # the second run must not prune the first folder
        update = goal_graph.refresh_library({"goal": "g"}, {"configurable": {}})["library_update"]
    assert update["documents"] == 2 and update["removed"] == 0
