"""The desk database: run trace and feedback schema (docs/SCOPE.md v3, "Feedback"). Offline: fake model, temp vault."""
import json
import sqlite3

import frontmatter
import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from test_goal_graph_flow import MD, Emb, fake_llm

from research_assistant import deep_report, desk, goal_graph
from research_assistant.knowledge import KnowledgeBase

REPORT = """# T

## Evidence status

| Section | Facts | Documents | Status |
|---|---|---|---|
| A | 2 | 2 | supported |

## Executive summary

Hybrid search reached 0.78 recall [E1].

## Recall

Hybrid search reached 0.78 recall on the test set [E1]. It beat BM25 at 0.61 recall [E1][E2].
A 4B model was used for pretraining [E2]. [cited; subject not in the cited evidence]
Small models need careful data selection overall. [inference]

| Model | Recall |
|---|---|
| Hybrid | 0.78 [E1] |

## Limitations

- Written by a small local model and checked by code.
"""


def rows(path, sql):
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        return [dict(r) for r in con.execute(sql)]


def test_D_T01_schema_creates_every_table_and_feedback_refuses_unknown_values(tmp_path):
    con = desk.connect(tmp_path / "d.sqlite")
    names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert names >= {"runs", "steps", "llm_calls", "retrievals", "judgements", "evidence", "section_inputs", "sentences",
                     "feedback"}
    con.execute("INSERT INTO feedback (created_at, target, target_ref, rating) VALUES ('t', 'chunk', 'E1', 'relevant')")
    con.commit()
    for target, rating in (("chunk", "great"), ("page", "relevant")):
        with pytest.raises(sqlite3.IntegrityError):
            con.execute("INSERT INTO feedback (created_at, target, target_ref, rating) VALUES ('t', ?, 'E1', ?)",
                        (target, rating))
        con.rollback()
    desk.connect(tmp_path / "d.sqlite").close()                                     # idempotent: opening again is fine
    assert con.execute("PRAGMA user_version").fetchone()[0] == 2                       # v2: rerank columns


def test_D_T02_report_sentences_keep_citations_and_flags_and_skip_tables_and_meta():
    s = desk.report_sentences(REPORT)
    assert {r["section"] for r in s} == {"Executive summary", "Recall"}
    recall = [r for r in s if r["section"] == "Recall"]
    assert [r["position"] for r in recall] == [1, 2, 3, 4]
    assert recall[1]["cites"] == ["E1", "E2"] and recall[1]["flag"] == ""
    assert recall[2]["flag"] == "subject" and "[cited;" not in recall[2]["text"] and "[E2]" in recall[2]["text"]
    assert recall[3]["flag"] == "inference" and recall[3]["cites"] == []
    assert not any("Hybrid | 0.78" in r["text"] for r in s)                          # table rows are not sentences


def test_D_T03_tracing_never_breaks_a_run(tmp_path, capsys):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    trace = desk.RunTrace(str(blocker), "r1")                                       # <vault> is a file: cannot create .desk
    trace.start_run("goal")
    with trace.step("plan"):
        trace.llm_call("planner", 0.1, "p", "a", True, True)
    assert "run trace not written" in capsys.readouterr().out
    desk.NULL.start_run("goal")                                                     # the no-op trace is silent


def test_D_T04_step_outcomes_ok_failed_and_current_trace(tmp_path):
    trace = desk.RunTrace(str(tmp_path), "r1")
    trace.start_run("g", "v3.0-hybrid", "qwen3.5:4b", {"collect_sources": True})
    with trace.step("plan"):
        assert desk.current() is trace
    assert desk.current() is desk.NULL
    with pytest.raises(ValueError), trace.step("write"):
        raise ValueError("boom")
    steps = rows(desk.db_path(str(tmp_path)), "SELECT name, outcome, error FROM steps ORDER BY id")
    assert steps[0] == {"name": "plan", "outcome": "ok", "error": ""}
    assert steps[1]["outcome"] == "failed" and "boom" in steps[1]["error"]
    run = rows(desk.db_path(str(tmp_path)), "SELECT * FROM runs")[0]
    assert run["engine"] == "v3.0-hybrid" and json.loads(run["settings"]) == {"collect_sources": True}


def test_D_T05_search_hits_carry_chunk_id_and_both_ranks(tmp_path):
    kb = KnowledgeBase(tmp_path / "kb.sqlite", Emb())
    kb.ingest_text("guide.md", MD, title="Hybrid Retrieval Guide")
    hit = kb.search("hybrid recall", k=1)[0]
    assert isinstance(hit["chunk_id"], int) and hit["vector_rank"] == 1 and hit["keyword_rank"] == 1


@pytest.fixture
def traced_flow(tmp_path, monkeypatch):
    prompts: list[str] = []
    kb = KnowledgeBase(tmp_path / "kb.sqlite", Emb())
    kb.ingest_text("guide.md", MD, title="Hybrid Retrieval Guide")
    kb.close = lambda: None
    inner = fake_llm(prompts)

    def raw(prompt, json_mode=False):                    # a section long enough to count as a sentence (4+ words)
        out = inner(prompt, json_mode)
        return "Hybrid search helps recall a lot [E1]." if out == "Hybrid helps [E1]." else out
    llm = deep_report.resilient(lambda prompt, json_mode, attempt: raw(prompt, json_mode), role="writer")
    monkeypatch.setattr(goal_graph, "build_llms", lambda cfg: {"planner": llm, "extractor": llm, "writer": llm, "thinker": llm})
    monkeypatch.setattr(goal_graph, "open_kb", lambda cfg: kb)
    vault = tmp_path / "vault"
    monkeypatch.setenv("VAULT_PATH", str(vault))
    g = goal_graph._graph(InMemorySaver())
    cfg = {"configurable": {"thread_id": "run-1", "min_section_facts": 1, "min_section_documents": 1,
                            "min_supported_share": 0.0}}
    return g, cfg, vault


def test_D_T06_a_full_graph_run_is_traced_end_to_end(traced_flow):
    g, cfg, vault = traced_flow
    g.invoke({"goal": "Does hybrid help?"}, cfg)                                   # pauses: clarify
    g.invoke(Command(resume="any audience"), cfg)                                  # pauses: approve plan
    out = g.invoke(Command(resume={"approved": True}), cfg)
    db = desk.db_path(str(vault))

    run = rows(db, "SELECT * FROM runs")[0]
    assert run["run_id"] == "run-1" and run["outcome"] == "complete" and run["engine"] == deep_report.engine_version(True)
    assert json.loads(run["plan"])["questions"] == ["Does hybrid help recall?"]
    assert run["report_path"] == out["report_path"]

    steps = rows(db, "SELECT name, outcome FROM steps ORDER BY id")
    assert {"name": "clarify", "outcome": "paused"} in steps                       # waiting for the user is not a failure
    assert {"name": "research", "outcome": "ok"} in steps and {"name": "save", "outcome": "ok"} in steps

    ret = rows(db, "SELECT * FROM retrievals")
    assert ret and ret[0]["question_idx"] == 0 and ret[0]["chunk_id"] and ret[0]["text_hash"]
    assert "Does hybrid help recall?" in json.loads(ret[0]["queries"])
    judged = rows(db, "SELECT * FROM judgements")
    assert judged and judged[0]["score"] == 3 and judged[0]["kept"] == 1 and judged[0]["eid"] == "E1"
    ev = rows(db, "SELECT * FROM evidence")
    assert ev[0]["eid"] == "E1" and ev[0]["chunk_id"] == ret[0]["chunk_id"] and ev[0]["doc_title"] == "Hybrid Retrieval Guide"
    inputs = rows(db, "SELECT * FROM section_inputs")
    assert inputs and inputs[0]["eid"] == "E1" and inputs[0]["included"] == 1 and inputs[0]["prompt_chars"] > 0
    sents = rows(db, "SELECT * FROM sentences")
    assert any(s["text"].startswith("Hybrid search helps") and json.loads(s["cites"]) == ["E1"] for s in sents)
    assert all(len(s["sentence_key"]) == 16 for s in sents)
    calls = rows(db, "SELECT step, role, ok FROM llm_calls")
    assert {c["step"] for c in calls} >= {"plan", "research", "write"} and all(c["ok"] for c in calls)

    post = frontmatter.load(out["report_path"])
    assert post["run_id"] == "run-1" and post["engine"] == deep_report.engine_version(True)
