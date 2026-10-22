import json

from research_assistant import deep_report as d
from research_assistant import runlog


def test_record_lifecycle(tmp_path):
    log = runlog.RunLog(str(tmp_path), "t1")
    log.start("my goal", collect_sources=True)
    log.step("plan", "Planning")
    log.progress(questions_done=1, questions_total=4)
    log.waiting("approve")
    run = runlog.read_run(str(tmp_path), "t1")
    assert run["goal"] == "my goal" and run["status"] == "waiting" and run["waiting_for"] == "approve"
    assert run["progress"] == {"questions_done": 1, "questions_total": 4}
    log.step("research")
    assert runlog.read_run(str(tmp_path), "t1")["status"] == "running"
    log.finish("C:/x/report.md", {"words": 10})
    run = runlog.read_run(str(tmp_path), "t1")
    assert run["status"] == "done" and run["report_path"] == "C:/x/report.md"
    assert [e["text"] for e in run["events"]] == ["Planning", "Report saved"]


def test_failure_is_recorded(tmp_path):
    log = runlog.RunLog(str(tmp_path), "t2")
    log.start("g")
    log.fail("Ollama is down")
    run = runlog.read_run(str(tmp_path), "t2")
    assert run["status"] == "failed" and "Ollama" in run["error"]


def test_list_runs_newest_first_without_events_or_partials(tmp_path, monkeypatch):
    ticks = iter(range(1000))                       # a clock that always moves: real ones tie within a millisecond on CI
    monkeypatch.setattr(runlog, "_now", lambda: f"2026-01-01T00:00:00.{next(ticks):03d}+00:00")
    a, b = runlog.RunLog(str(tmp_path), "a"), runlog.RunLog(str(tmp_path), "b")
    a.start("first")
    b.start("second")
    b.event("later")
    b.save_partial(1, [])
    runs = runlog.list_runs(str(tmp_path))
    assert [r["id"] for r in runs] == ["b", "a"]
    assert all("events" not in r for r in runs)


def test_no_vault_or_bad_id_is_a_silent_noop(tmp_path):
    for log in (runlog.RunLog("", "t"), runlog.RunLog(str(tmp_path), "../evil"), runlog.RunLog(str(tmp_path), "")):
        log.start("g")
        log.step("x", "y")
        log.finish()
        assert log.load_partial() == (0, [])
    assert not (tmp_path / ".runs").exists()
    assert runlog.read_run(str(tmp_path), "../evil") is None


def test_events_are_capped(tmp_path):
    log = runlog.RunLog(str(tmp_path), "t")
    for i in range(runlog.MAX_EVENTS + 50):
        log.event(f"e{i}")
    events = runlog.read_run(str(tmp_path), "t")["events"]
    assert len(events) == runlog.MAX_EVENTS and events[-1]["text"] == f"e{runlog.MAX_EVENTS + 49}"


def test_corrupt_record_does_not_crash(tmp_path):
    (tmp_path / ".runs").mkdir()
    (tmp_path / ".runs" / "t.json").write_text("{not json", encoding="utf-8")
    assert runlog.read_run(str(tmp_path), "t") is None
    runlog.RunLog(str(tmp_path), "t").event("recovers")
    assert runlog.read_run(str(tmp_path), "t")["events"][0]["text"] == "recovers"


def test_partial_evidence_roundtrip_and_clear(tmp_path):
    log = runlog.RunLog(str(tmp_path), "t")
    log.save_partial(2, [{"id": "E1"}])
    assert log.load_partial() == (2, [{"id": "E1"}])
    log.clear_partial()
    assert log.load_partial() == (0, [])
    (tmp_path / ".runs" / "t.evidence.json").write_text(json.dumps({"questions_done": "x"}), encoding="utf-8")
    assert log.load_partial() == (0, [])


# ---- gather_evidence: progress and resume --------------------------------------------------------

def _plan():
    return d.Plan(goal="g", title="T", sub_questions=["q1", "q2", "q3"],
                  outline=[{"title": "S", "questions": [0, 1, 2]}])


def _search(q):
    return [{"title": f"Doc-{q}", "text": f"Fact about {q} is stated here in this passage of text.", "path": q}]


def _llm(prompt, json_mode=False):
    if "supported" in prompt:
        return '{"supported": true}'
    q = "q1" if "q1" in prompt else "q2" if "q2" in prompt else "q3"
    return json.dumps({"facts": [{"claim": f"claim {q}", "quote": f"Fact about {q} is stated here"}]})


def test_progress_is_reported_after_each_question():
    seen = []
    d.gather_evidence(_plan(), _search, _llm, on_question_done=lambda done, total, ev: seen.append((done, total, len(ev))))
    assert seen == [(1, 3, 1), (2, 3, 2), (3, 3, 3)]


def test_resume_skips_finished_questions_and_keeps_their_evidence():
    first = []
    d.gather_evidence(_plan(), _search, _llm, on_question_done=lambda done, total, ev: first.append((done, list(ev))))
    done2, ev2 = first[1]
    calls = []

    def counting_llm(prompt, json_mode=False):
        calls.append(prompt[:30])
        return _llm(prompt, json_mode)

    out = d.gather_evidence(_plan(), _search, counting_llm, resume=(done2, ev2))
    assert [e.id for e in out] == ["E1", "E2", "E3"]
    assert all("q1" not in c and "q2" not in c for c in calls if "Question" in c)
    assert len(out) == 3


# ---- plan feedback that steers rather than adds ---------------------------------------------------

def test_steering_feedback_does_not_become_a_section():
    plan = d.Plan(goal="g", title="T", sub_questions=["q1"], outline=[{"title": "S", "questions": [0]}])
    for note in ("keep it focused on retrieval quality", "make it shorter", "Please be more concrete", "avoid jargon"):
        assert d._notes_intent(note)[0] == "steer"
        out = d.enforce_notes(d.Plan(goal="g", title="T", sub_questions=list(plan.sub_questions),
                                     outline=[dict(s) for s in plan.outline]), note)
        assert out.sub_questions == ["q1"] and [s["title"] for s in out.outline] == ["S"]


def test_add_and_remove_requests_still_work():
    assert d._notes_intent("add a section on cost")[0] == "add"
    assert d._notes_intent("drop the history of RAG")[0] == "remove"
    plan = d.Plan(goal="g", title="T", sub_questions=["q1"], outline=[{"title": "S", "questions": [0]}])
    assert any("Cost" in s["title"] for s in d.enforce_notes(plan, "add a section on cost").outline)


# ---- a plan always ends with the recommendations section -------------------------------------------

def test_a_plan_always_ends_with_a_synthesis_section():
    outline = [{"title": "A", "questions": [0], "brief": "a"}, {"title": "B", "questions": [1], "brief": "b"}]
    llm = lambda prompt, json_mode=False: json.dumps({"title": "T", "sub_questions": ["q1", "q2"], "outline": outline})  # noqa: E731
    plan = d.make_plan("goal", llm)
    assert plan.outline[-1]["synthesis"] is True and plan.outline[-1]["questions"] == []
    assert [s["title"] for s in plan.outline[:2]] == ["A", "B"] and not plan.outline[0]["synthesis"]
    assert sorted(i for s in plan.outline for i in s["questions"]) == [0, 1]    # every question still in one section


def test_a_model_supplied_synthesis_section_is_not_duplicated():
    outline = [{"title": "A", "questions": [0, 1], "brief": "a"}, {"title": "Recommendations", "questions": [], "brief": "r"}]
    llm = lambda prompt, json_mode=False: json.dumps({"title": "T", "sub_questions": ["q1", "q2"], "outline": outline})  # noqa: E731
    plan = d.make_plan("goal", llm)
    assert [s["title"] for s in plan.outline] == ["A", "Recommendations"] and plan.outline[-1]["synthesis"]
