"""Small fixes from the close-out review: Stop, the run record, labels, source ids and ordering."""

import json
from pathlib import Path

import pytest

from research_assistant import collector as c
from research_assistant import deep_report as d
from research_assistant import goal_graph, runlog
from research_assistant import report_checks as rc

# ---- Stop is not undone by the next step, and stops a step before it begins ---------------------------

def test_a_stop_pressed_between_steps_survives_the_next_step(tmp_path):
    log = runlog.RunLog(str(tmp_path), "t")
    log.start("g")
    log.step("plan")
    log._mutate(lambda x: x.update(status="stopped"))               # what the dashboard's Stop does
    log.step("research", "Extracting")                              # the next node starts
    rec = runlog.read_run(str(tmp_path), "t")
    assert rec["status"] == "stopped" and rec["step"] == "research" and log.is_stopped()


def test_a_step_does_not_begin_after_stop(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    ran = []

    @goal_graph.tracked("library", "x")
    def node(state, config):
        ran.append(1)
        return {}

    config = {"configurable": {"thread_id": "t"}}
    node({"goal": "g"}, config)
    assert ran == [1]
    runlog.RunLog(str(tmp_path), "t")._mutate(lambda x: x.update(status="stopped"))
    with pytest.raises(d.RunStopped):
        node({"goal": "g"}, config)
    assert ran == [1]                                               # the second step never ran
    deep_stop_cleanup()


def deep_stop_cleanup():
    d.set_stop_check(None)


def test_stop_is_not_swallowed_by_the_coverage_and_discover_nodes(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))

    def stopped(*a, **k):
        raise d.RunStopped()

    monkeypatch.setattr(d, "coverage", stopped)
    monkeypatch.setattr(goal_graph, "open_kb", lambda cfg: _NullKb())
    monkeypatch.setattr(goal_graph, "build_llms", lambda cfg: {"planner": None})
    state = {"goal": "g", "plan": {"goal": "g", "title": "T", "sub_questions": ["q?"], "outline": []}}
    with pytest.raises(d.RunStopped):
        goal_graph.check_coverage(state, {"configurable": {"thread_id": "t"}})
    monkeypatch.setattr(c, "discover", stopped)
    with pytest.raises(d.RunStopped):
        goal_graph.discover({**state, "collect_mode": "all"}, {"configurable": {"thread_id": "t"}})
    deep_stop_cleanup()


class _NullKb:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


# ---- an unreadable record is not replaced by an empty one ----------------------------------------------

def test_a_failed_read_skips_the_write_instead_of_wiping_the_history(tmp_path, monkeypatch):
    log = runlog.RunLog(str(tmp_path), "t")
    log.start("my goal")
    log.event("first")
    real = Path.read_text

    def locked(self, *a, **k):
        if self.name == "t.json":
            raise PermissionError("sharing violation")
        return real(self, *a, **k)

    monkeypatch.setattr(Path, "read_text", locked)
    log.event("lost, but harmless")                                  # the read fails: this write is skipped
    monkeypatch.setattr(Path, "read_text", real)
    rec = runlog.read_run(str(tmp_path), "t")
    assert rec["goal"] == "my goal" and [e["text"] for e in rec["events"]] == ["first"]


def test_a_corrupt_record_still_starts_afresh(tmp_path):
    (tmp_path / ".runs").mkdir()
    (tmp_path / ".runs" / "t.json").write_text("{broken", encoding="utf-8")
    runlog.RunLog(str(tmp_path), "t").event("recovers")
    assert runlog.read_run(str(tmp_path), "t")["events"][0]["text"] == "recovers"


# ---- labels: a citation does not make an invented number true -----------------------------------------

def _ev(i, source, claim, quote="quote text for it"):
    return d.Evidence(id=f"E{i}", claim=claim, quote=quote, source=source, heading="", sub_questions=[0])


BY_ID = {"E1": _ev(1, "A", "Fertility is 2.1 tokens per word"), "E2": _ev(2, "B", "Vocabulary has 32000 entries")}
KNOWN = rc.evidence_numbers(list(BY_ID.values()))


def test_a_cited_sentence_with_a_number_not_in_its_evidence_is_flagged():
    out = rc.label_text("Pretraining costs 15000 dollars in total [E1][E2].", BY_ID, KNOWN)
    assert "[cited; figure not in the cited evidence]" in out and "[established]" not in out


def test_a_cited_sentence_with_numbers_from_its_evidence_is_still_established():
    out = rc.label_text("Fertility is 2.1 and the vocabulary has 32000 entries [E1][E2].", BY_ID, KNOWN)
    assert out.endswith("[established]")


def test_the_citation_number_itself_is_not_treated_as_a_figure():
    assert rc.label_text("The vocabulary has a size of 32000 entries here [E2].", BY_ID, KNOWN).endswith("[single source]")


def test_a_citation_after_the_full_stop_belongs_to_the_sentence_before_it():
    out = rc.label_text("Fertility is 2.1 tokens per word. [E1] Another sentence is written here without support.", BY_ID, KNOWN)
    assert "Fertility is 2.1 tokens per word. [E1] [single source]" in out
    assert out.count("[inference]") == 1                             # only the second sentence


# ---- source ids, ordering, PDF names ------------------------------------------------------------------

def test_two_pages_with_the_same_title_get_different_ids_and_the_same_page_the_same_id():
    a = c._web_candidate(c.Hit("Home | who.int", "https://who.int/a", ""), "q")
    b = c._web_candidate(c.Hit("Home | who.int", "https://who.int/b", ""), "q")
    again = c._web_candidate(c.Hit("Home | who.int", "https://who.int/a?utm_source=x", ""), "q")
    assert a.id != b.id and a.id == again.id


def test_chosen_sources_come_before_seed_urls(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    seen = {}

    def fake(todo, store, fx, **kw):
        seen["urls"] = [x.url for x in todo]
        return {"saved": 0, "pages": 0, "papers": 0, "skipped": 0, "failed": 0, "folder": ""}

    monkeypatch.setattr(c, "collect_selected", fake)
    cand = c._web_candidate(c.Hit("Picked", "https://picked.example/p", ""), "q")
    d_ = c.to_dict(cand, 0)
    state = {"goal": "g", "plan": {"title": "T", "sub_questions": ["q"]}, "candidates": [d_], "selected_ids": [d_["id"]]}
    goal_graph.collect(state, {"configurable": {"thread_id": "t", "seed_urls": "https://seed.example/x"}})
    assert seen["urls"] == ["https://picked.example/p", "https://seed.example/x"]


def test_an_old_style_arxiv_id_makes_a_safe_file_name(monkeypatch):
    names = []
    monkeypatch.setattr(goal_graph, "convert_to_markdown", lambda path: names.append(path.name) or "text")
    goal_graph._pdf_to_markdown(b"%PDF", "hep-th/9901001")
    assert names == ["hep-th-9901001.pdf"]


def test_gaps_without_coverage_says_so_and_searches_everything(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    seen = {}
    monkeypatch.setattr(c, "discover", lambda questions, **k: seen.update(q=list(questions)) or [])
    monkeypatch.setattr(goal_graph, "build_llms", lambda cfg: {"planner": None})
    state = {"goal": "g", "plan": {"title": "T", "sub_questions": ["a?", "b?"]}, "collect_mode": "gaps", "coverage": []}
    goal_graph.discover(state, {"configurable": {"thread_id": "t"}})
    assert seen["q"] == ["a?", "b?"]
    events = [e["text"] for e in runlog.read_run(str(tmp_path), "t")["events"]]
    assert any("No coverage information" in e for e in events)


def test_the_limitations_do_not_overclaim():
    p = d.Plan(goal="g", title="T", sub_questions=["q"], outline=[{"title": "S", "questions": [0]}])
    ev = [_ev(i, "A" if i % 2 else "B", f"claim {i}") for i in range(1, 7)]
    report = d.assemble(p, [("S", "Text here is long enough [E1].")], ev, lambda *a, **k: json.dumps({}) and "Summary.",
                        standards=rc.Standards(3, 2, 0.5))
    assert "checked twice: by code" in report and "Every prose sentence of four or more words" in report
    assert "passed two automatic checks" not in report
