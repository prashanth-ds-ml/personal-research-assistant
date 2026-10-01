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
    note = goal_graph._scope_note({"saved": 3, "pages": 2, "papers": 1, "skipped": 4})
    assert "3 new source(s) (2 web page(s), 1 paper(s)) were collected" in note and "less reliable" in note
    assert "found nothing new" in goal_graph._scope_note({"saved": 0})


def test_collect_warns_when_fewer_sources_were_indexed_than_saved(flow, monkeypatch):
    g, cfg, _, tmp_path = flow
    monkeypatch.undo()                                              # use the real open_kb for this test
    monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault2"))
    monkeypatch.setenv("KB_PATH", str(tmp_path / "kb2.sqlite"))
    monkeypatch.setattr(goal_graph, "make_embeddings", lambda *a, **k: Emb())

    def fake_collect(todo, store, fx, **kw):
        store.dir.mkdir(parents=True, exist_ok=True)
        (store.dir / "good.md").write_text("# Good\n\nHybrid retrieval reached 0.78 recall in this study of search.")
        (store.dir / "blank.md").write_text("")                     # saved but nothing indexable
        return {"saved": 2, "pages": 2, "papers": 0, "skipped": 0, "failed": 0, "folder": str(store.dir)}

    monkeypatch.setattr(goal_graph.collector, "collect_selected", fake_collect)
    cand = goal_graph.collector._web_candidate(goal_graph.collector.Hit("P", "https://a.example/p", ""), "q?")
    state = {"goal": "g", "plan": {"goal": "g", "title": "T", "sub_questions": ["q?"], "outline": []},
             "candidates": [goal_graph.collector.to_dict(cand, 0)], "selected_ids": [f"web:{cand.id}"]}
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


# ---- run record (what the dashboard's Runs page reads) ---------------------------------------------

def _record(tmp_path, run_id="t"):
    from research_assistant import runlog
    return runlog.read_run(str(tmp_path / "vault"), run_id)


def test_run_record_follows_the_whole_flow(flow):
    g, cfg, _, tmp_path = flow
    g.invoke({"goal": "Does hybrid help?"}, cfg)
    rec = _record(tmp_path)
    assert rec["status"] == "waiting" and rec["waiting_for"] == "clarify" and rec["goal"] == "Does hybrid help?"
    g.invoke(Command(resume="any audience"), cfg)
    assert _record(tmp_path)["waiting_for"] == "approve"
    out = g.invoke(Command(resume={"approved": True}), cfg)
    rec = _record(tmp_path)
    assert rec["status"] == "done" and rec["report_path"] == out["report_path"] and rec["waiting_for"] is None
    assert rec["progress"]["questions_done"] == 1 and rec["progress"]["questions_total"] == 1
    assert rec["progress"]["sections_done"] == rec["progress"]["sections_total"]
    texts = [e["text"] for e in rec["events"]]
    assert any(t.startswith("Plan:") for t in texts) and "Report saved" in texts
    assert not (tmp_path / "vault" / ".runs" / "t.evidence.json").exists()      # partial evidence cleaned up


def test_a_failed_run_is_recorded_with_its_reason(flow, monkeypatch):
    g, cfg, _, tmp_path = flow
    to_first_plan(g, cfg)

    def boom(*a, **k):
        raise RuntimeError("the model fell over")

    monkeypatch.setattr(deep_report, "gather_evidence", boom)
    with pytest.raises(RuntimeError):
        g.invoke(Command(resume={"approved": True}), cfg)
    rec = _record(tmp_path)
    assert rec["status"] == "failed" and "fell over" in rec["error"] and rec["step"] == "research"


def test_a_retry_resumes_after_the_questions_already_finished(flow, monkeypatch):
    g, cfg, _, tmp_path = flow
    to_first_plan(g, cfg)
    from research_assistant import runlog
    log = runlog.RunLog(str(tmp_path / "vault"), "t")
    seen = {}
    real = deep_report.gather_evidence

    def spy(*a, **k):
        seen["resume"] = k.get("resume")
        return real(*a, **k)

    log.save_partial(1, [{"id": "E1", "claim": "Hybrid retrieval reached 0.78 recall",
                          "quote": "Hybrid retrieval reached 0.78 recall", "source": "Hybrid Retrieval Guide",
                          "heading": "", "sub_questions": [0]}])
    monkeypatch.setattr(deep_report, "gather_evidence", spy)
    g.invoke(Command(resume={"approved": True}), cfg)
    assert seen["resume"][0] == 1 and seen["resume"][1][0].id == "E1"


# ---- discover -> review -> collect (the source-collector steps) ------------------------------------------

def _cand(i, score):
    c = goal_graph.collector._web_candidate(goal_graph.collector.Hit(f"Page {i}", f"https://s{i}.example/p", "x"), "q")
    c.relevance = score
    return goal_graph.collector.to_dict(c, 0)


def test_the_run_pauses_to_show_candidates_and_collects_only_the_chosen(flow, monkeypatch):
    g, cfg, _, tmp_path = flow
    cands = [_cand(1, 3), _cand(2, 2), _cand(3, 1)]
    monkeypatch.setattr(goal_graph.collector, "discover", lambda *a, **k: cands)
    got = {}

    def fake_collect(todo, store, fx, **kw):
        got["titles"] = [c.title for c in todo]
        return {"saved": 0, "pages": 0, "papers": 0, "skipped": 0, "failed": 0, "folder": ""}

    monkeypatch.setattr(goal_graph.collector, "collect_selected", fake_collect)
    cfg = {"configurable": {**cfg["configurable"], "collect_sources": True}}
    g.invoke({"goal": "Does hybrid help?"}, cfg)
    g.invoke(Command(resume="any audience"), cfg)
    shown = interrupt_value(g.invoke(Command(resume={"approved": True}), cfg))
    assert shown["type"] == "review_sources" and [c["title"] for c in shown["candidates"]] == ["Page 1", "Page 2", "Page 3"]
    rec = _record(tmp_path)
    assert rec["status"] == "waiting" and rec["waiting_for"] == "review"
    out = g.invoke(Command(resume={"selected": [cands[1]["id"], "web:not-offered", cands[1]["id"]]}), cfg)
    assert got["titles"] == ["Page 2"]                       # an id that was never offered is ignored; no duplicates
    assert out["report_path"]


def test_an_unreadable_choice_is_asked_again_then_collects_nothing(flow, monkeypatch):
    g, cfg, _, _ = flow
    monkeypatch.setattr(goal_graph.collector, "discover", lambda *a, **k: [_cand(1, 3)])
    calls = []
    monkeypatch.setattr(goal_graph.collector, "collect_selected", lambda todo, *a, **k: calls.append(todo) or {
        "saved": 0, "pages": 0, "papers": 0, "skipped": 0, "failed": 0, "folder": ""})
    cfg = {"configurable": {**cfg["configurable"], "collect_sources": True}}
    g.invoke({"goal": "g"}, cfg)
    g.invoke(Command(resume=""), cfg)
    g.invoke(Command(resume={"approved": True}), cfg)
    again = interrupt_value(g.invoke(Command(resume="yes all of them"), cfg))
    assert "Not understood" in again["error"]
    g.invoke(Command(resume=["still wrong"]), cfg)
    assert calls == []                                        # nothing was collected


def test_with_review_off_everything_above_the_minimum_is_collected(flow, monkeypatch):
    g, cfg, _, _ = flow
    monkeypatch.setattr(goal_graph.collector, "discover", lambda *a, **k: [_cand(1, 3), _cand(2, 2)])
    got = {}
    monkeypatch.setattr(goal_graph.collector, "collect_selected", lambda todo, *a, **k: got.update(t=[c.title for c in todo]) or {
        "saved": 0, "pages": 0, "papers": 0, "skipped": 0, "failed": 0, "folder": ""})
    cfg = {"configurable": {**cfg["configurable"], "collect_sources": True, "collect_review": False}}
    g.invoke({"goal": "g"}, cfg)
    g.invoke(Command(resume=""), cfg)
    out = g.invoke(Command(resume={"approved": True}), cfg)
    assert got["t"] == ["Page 1"] and out["report_path"]     # default minimum relevance is 3


def test_discovery_failure_never_stops_the_run(flow, monkeypatch):
    g, cfg, _, tmp_path = flow

    def boom(*a, **k):
        raise RuntimeError("search engine blocked us")

    monkeypatch.setattr(goal_graph.collector, "discover", boom)
    cfg = {"configurable": {**cfg["configurable"], "collect_sources": True}}
    g.invoke({"goal": "g"}, cfg)
    g.invoke(Command(resume=""), cfg)
    out = g.invoke(Command(resume={"approved": True}), cfg)     # no review pause: nothing was found
    assert out["report_path"]
    assert any("Source search failed" in e["text"] for e in _record(tmp_path)["events"])


def test_nothing_is_searched_unless_fetching_is_switched_on(flow, monkeypatch):
    g, cfg, _, _ = flow

    def boom(*a, **k):
        raise AssertionError("must not search")

    monkeypatch.setattr(goal_graph.collector, "discover", boom)
    g.invoke({"goal": "g"}, cfg)
    g.invoke(Command(resume=""), cfg)
    assert g.invoke(Command(resume={"approved": True}), cfg)["report_path"]


# ---- per-run options survive the pauses; Stop reaches a running call ---------------------------------------

def test_options_sent_only_with_the_first_call_still_apply_after_each_pause(flow, monkeypatch):
    """The dashboard sends collect_sources / seed_urls only when it starts the run; every resume carries no config."""
    g, cfg, _, _ = flow
    searched = []

    def fake_discover(questions, **k):
        searched.append(questions)
        return [_cand(1, 3)]

    monkeypatch.setattr(goal_graph.collector, "discover", fake_discover)
    got = {}
    monkeypatch.setattr(goal_graph.collector, "collect_selected", lambda todo, *a, **k: got.update(t=[c.url for c in todo]) or {
        "saved": 0, "pages": 0, "papers": 0, "skipped": 0, "failed": 0, "folder": ""})
    start = {"configurable": {**cfg["configurable"], "collect_sources": True, "seed_urls": "https://seed.example/a"}}
    resume = {"configurable": dict(cfg["configurable"])}              # what a resume really carries: no options
    g.invoke({"goal": "Does hybrid help?"}, start)
    g.invoke(Command(resume="any audience"), resume)
    shown = interrupt_value(g.invoke(Command(resume={"approved": True}), resume))
    assert searched and shown["type"] == "review_sources"           # the checkbox was remembered
    g.invoke(Command(resume={"selected": [shown["candidates"][0]["id"]]}), resume)
    assert "https://seed.example/a" in got["t"]                     # and so were the seed URLs


def test_stop_ends_a_run_without_marking_it_failed(flow, monkeypatch):
    from research_assistant import runlog
    g, cfg, _, tmp_path = flow
    to_first_plan(g, cfg)
    log = runlog.RunLog(str(tmp_path / "vault"), "t")
    real = deep_report.gather_evidence

    def stop_then_ask(*a, **k):
        log._mutate(lambda d: d.update(status="stopped"))           # what the dashboard's Stop button does
        return real(*a, **k)

    monkeypatch.setattr(deep_report, "gather_evidence", stop_then_ask)
    with pytest.raises(deep_report.RunStopped):
        g.invoke(Command(resume={"approved": True}), cfg)
    assert runlog.read_run(str(tmp_path / "vault"), "t")["status"] == "stopped"      # not "failed"
    deep_report.set_stop_check(None)
