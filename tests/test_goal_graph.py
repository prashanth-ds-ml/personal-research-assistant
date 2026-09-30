"""The deep_research graph pauses for the user twice (clarify, approve plan) and
only then spends time on extraction and writing. Offline: fake LLM, fake
embeddings, in-memory checkpointer."""

import json

import pytest
from langchain_core.embeddings import Embeddings
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from research_assistant import goal_graph
from research_assistant.knowledge import KnowledgeBase

MD = "# Hybrid Retrieval Guide\n\n## Results\nHybrid retrieval reached 0.78 recall, beating BM25 at 0.61 recall.\n"


class KeywordEmbeddings(Embeddings):
    def _e(self, t):
        t = t.lower()
        v = [float(t.count(k)) for k in ("hybrid", "recall", "bm25")]
        return v if any(v) else [0.001] * 3

    def embed_documents(self, texts):
        return [self._e(t) for t in texts]

    def embed_query(self, text):
        return self._e(text)


class Calls:
    def __init__(self):
        self.prompts = []


@pytest.fixture
def wired(tmp_path, monkeypatch):
    calls = Calls()

    def llm(prompt, json_mode=False):
        calls.prompts.append(prompt)
        if "clarifying questions" in prompt:
            return json.dumps({"questions": ["Which audience?", "Which region?"]})
        if "research methodologist" in prompt:
            extra = "SECTION-ON-COST" if "add a section on cost" in prompt else "SECTION-ON-RECALL"
            return json.dumps({"title": "Hybrid report", "sub_questions": ["Does hybrid help recall?"],
                               "outline": [{"title": extra, "questions": [0], "brief": "b"}]})
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

    kb = KnowledgeBase(tmp_path / "kb.sqlite", KeywordEmbeddings())
    kb.ingest_text("guide.md", MD, title="Hybrid Retrieval Guide")
    monkeypatch.setattr(goal_graph, "build_llms", lambda cfg: {"planner": llm, "extractor": llm, "writer": llm})
    kb.close = lambda: None          # the fake open_kb hands the SAME instance to every node; a real one is closed per node
    monkeypatch.setattr(goal_graph, "open_kb", lambda cfg: kb)
    g = goal_graph._graph(InMemorySaver())
    monkeypatch.setenv("VAULT_PATH", str(tmp_path / "vault"))     # paths come from the environment, never per run
    cfg = {"configurable": {"thread_id": "t1"}}
    return g, cfg, calls, tmp_path


def test_pauses_for_clarification_then_for_plan_then_writes_report(wired):
    g, cfg, calls, tmp_path = wired

    out = g.invoke({"goal": "Should we use hybrid retrieval?"}, cfg)
    q = out["__interrupt__"][0].value
    assert q["type"] == "clarify" and q["questions"] == ["Which audience?", "Which region?"]
    assert not any("Extract facts" in p for p in calls.prompts)  # nothing expensive yet

    out = g.invoke(Command(resume="Audience: clinicians. Region: India."), cfg)
    plan_req = out["__interrupt__"][0].value
    assert plan_req["type"] == "approve_plan" and plan_req["plan"]["title"] == "Hybrid report"
    # the user's answers reached the planner
    assert any("Audience: clinicians" in p for p in calls.prompts if "research methodologist" in p)
    assert not any("Extract facts" in p for p in calls.prompts)  # still waiting on approval

    out = g.invoke(Command(resume={"approved": True}), cfg)
    assert "__interrupt__" not in out
    assert "Hybrid helps [E1]." in out["report"] and out["stats"]["evidence"] == 1
    saved = next((tmp_path / "vault" / "Research").glob("*.md"))
    assert saved.read_text(encoding="utf-8").startswith("---")
    assert out["report_path"] == str(saved)


def test_plan_feedback_triggers_a_revised_plan_before_any_extraction(wired):
    g, cfg, calls, _ = wired
    g.invoke({"goal": "Should we use hybrid retrieval?"}, cfg)
    g.invoke(Command(resume=""), cfg)  # skip clarification answers

    out = g.invoke(Command(resume={"feedback": "add a section on cost"}), cfg)
    revised = out["__interrupt__"][0].value
    assert revised["type"] == "approve_plan" and revised["revisions_left"] == 1
    assert revised["plan"]["outline"][0]["title"] == "SECTION-ON-COST"
    assert not any("Extract facts" in p for p in calls.prompts)

    out = g.invoke(Command(resume={"approved": True}), cfg)
    assert "SECTION-ON-COST" in out["report"]


def test_can_run_fully_autonomous_without_interrupts(wired):
    g, cfg, _, _ = wired
    cfg["configurable"].update(ask_clarifying_questions=False, require_plan_approval=False)
    out = g.invoke({"goal": "Should we use hybrid retrieval?"}, cfg)
    assert "__interrupt__" not in out and out["stats"]["sections"] == 1


def test_new_files_are_indexed_at_the_start_of_a_run(wired, monkeypatch):
    g, cfg, calls, tmp_path = wired
    lib = tmp_path / "MyLibrary"
    lib.mkdir()
    (lib / "new-paper.md").write_text("# New Paper\n\nBM25 recall improves with reranking, recall 0.91.")
    monkeypatch.setenv("LIBRARY_FOLDERS", str(lib))
    cfg["configurable"].update(ask_clarifying_questions=False, require_plan_approval=False)
    kb = goal_graph.open_kb(None)
    assert kb.stats()["documents"] == 1                      # only the fixture's guide.md

    g.invoke({"goal": "Does reranking help recall?"}, cfg)

    assert kb.stats()["documents"] == 2                       # new-paper.md was indexed by the run
    assert any(h["path"] == "MyLibrary/new-paper.md" for h in kb.search("reranking recall", k=3))


def test_unchanged_folder_is_a_cheap_noop_and_can_be_switched_off(wired, monkeypatch):
    g, cfg, _, tmp_path = wired
    lib = tmp_path / "Lib"
    lib.mkdir()
    (lib / "a.md").write_text("# A\n\nhybrid recall")
    state = {"goal": "x"}
    monkeypatch.setenv("LIBRARY_FOLDERS", str(lib))
    base = {"configurable": dict(cfg["configurable"])}
    first = goal_graph.refresh_library(state, base)["library_update"]
    second = goal_graph.refresh_library(state, base)["library_update"]
    assert first["added"] == 1 and second["added"] == 0
    off = {"configurable": {**base["configurable"], "auto_ingest": False}}
    assert goal_graph.refresh_library(state, off) == {"library_update": {}}


def test_ingest_failure_never_blocks_the_run(wired, monkeypatch):
    g, cfg, _, tmp_path = wired
    lib = tmp_path / "Lib2"
    lib.mkdir()
    (lib / "a.md").write_text("# A\n\nhybrid recall")
    monkeypatch.setattr(goal_graph, "open_kb", lambda c: (_ for _ in ()).throw(RuntimeError("ollama down")))
    monkeypatch.setenv("LIBRARY_FOLDERS", str(lib))
    out = goal_graph.refresh_library({"goal": "x"}, {"configurable": {}})
    assert "ollama down" in out["library_update"]["error"]


def test_default_folders_are_vault_sources_and_library(tmp_path):
    from research_assistant.configuration import Configuration

    (tmp_path / "Sources").mkdir()
    (tmp_path / "Library").mkdir()
    cfg = Configuration(vault_path=str(tmp_path))
    assert {p.name for p in goal_graph.library_folders(cfg)} == {"Sources", "Library"}
    assert goal_graph.library_folders(Configuration(vault_path=str(tmp_path / "missing"))) == []


def _plan_state():
    return {"goal": "g", "plan": {"goal": "g", "title": "Hybrid report", "sub_questions": ["Does hybrid help?"],
                                  "outline": [{"title": "S", "questions": [0], "brief": ""}]}}


def test_collect_is_skipped_unless_asked_for(wired, monkeypatch):
    _, cfg, _, _ = wired
    monkeypatch.setattr(goal_graph.fetcher, "collect", lambda *a, **k: (_ for _ in ()).throw(AssertionError("called")))
    assert goal_graph.collect(_plan_state(), cfg) == {}                     # default: off, no seeds


def test_collect_saves_then_indexes_so_the_same_run_can_cite_the_new_sources(wired, monkeypatch):
    _, cfg, _, tmp_path = wired
    kb = goal_graph.open_kb(None)

    def fake_collect(questions, store, fx, llm, **kw):
        assert questions == ["Does hybrid help?"] and kw["max_sources"] == 10
        store.dir.mkdir(parents=True, exist_ok=True)
        (store.dir / "new.md").write_text("# New\n\nReranking lifted BM25 recall to 0.91 in our test.")
        (store.dir / "raw").mkdir()
        (store.dir / "raw" / "new.pdf").write_bytes(b"%PDF")              # original must NOT be indexed too
        return {"saved": 1, "skipped": 0, "failed": 0, "folder": str(store.dir)}

    monkeypatch.setattr(goal_graph.fetcher, "collect", fake_collect)
    cfg["configurable"].update(collect_sources=True)
    out = goal_graph.collect(_plan_state(), cfg)
    assert out["collect_report"]["saved"] == 1
    paths = [r[0] for r in kb.db.execute("SELECT path FROM docs").fetchall()]
    assert any(p.startswith("Library/") and p.endswith("new.md") for p in paths)
    assert not any(p.endswith(".pdf") for p in paths)                      # raw/ skipped


def test_collect_failure_is_reported_not_raised(wired, monkeypatch):
    _, cfg, _, _ = wired
    monkeypatch.setattr(goal_graph.fetcher, "collect", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("network down")))
    cfg["configurable"].update(collect_sources=True)
    assert "network down" in goal_graph.collect(_plan_state(), cfg)["collect_report"]["error"]


def test_seed_urls_alone_trigger_collect_and_bad_entries_are_ignored(wired, monkeypatch):
    _, cfg, _, _ = wired
    got = {}

    def fake_collect(questions, store, fx, llm, **kw):
        got.update(questions=questions, seeds=kw["seeds"])
        return {"saved": 0, "skipped": 0, "failed": 0, "folder": ""}

    monkeypatch.setattr(goal_graph.fetcher, "collect", fake_collect)
    cfg["configurable"].update(seed_urls="https://a.example/x; not-a-url\nhttps://b.example/y.pdf")
    goal_graph.collect(_plan_state(), cfg)
    assert got["seeds"] == ["https://a.example/x", "https://b.example/y.pdf"]
    assert got["questions"] == []                   # seeds only: no searching unless collect_sources is on
