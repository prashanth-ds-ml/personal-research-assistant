"""The final 'recommendations' section is synthesised from the other sections'
findings (recommendations cannot be retrieved from papers)."""

import json

from research_assistant import deep_report as d


def test_planner_marks_trailing_empty_section_as_synthesis_and_orphans_skip_it():
    llm = lambda p, json_mode=False: json.dumps({  # noqa: E731
        "title": "T", "sub_questions": ["a?", "b?", "c?"],
        "outline": [{"title": "Findings", "questions": [0], "brief": ""},
                    {"title": "Recommendations", "questions": [], "brief": ""}]})
    plan = d.make_plan("goal", llm)
    assert plan.outline[-1]["synthesis"] is True and plan.outline[-1]["questions"] == []
    assert sorted(plan.outline[0]["questions"]) == [0, 1, 2]  # orphans 1,2 went to the evidence section


def test_synthesis_cites_only_ids_from_prior_sections_and_runs_last():
    plan = d.Plan("goal", "T", ["q"], [
        {"title": "Findings", "questions": [0], "brief": "", "synthesis": False},
        {"title": "Recommendations", "questions": [], "brief": "", "synthesis": True}])
    ev = [d.Evidence("E1", "Hybrid beats BM25", "quote text here ok", "Doc", "", [0])]
    seen = {}

    def llm(prompt, json_mode=False):
        if "synthesis section" in prompt:
            seen["synth"] = prompt
            return "Adopt hybrid search first [E1]. An invented cite [E9]."
        return "Hybrid wins [E1]."

    sections = d.write_all(plan, ev, llm, standards=d.rc.Standards(1, 1, 0.0))
    assert [t for t, _ in sections] == ["Findings", "Recommendations"]
    assert "Hybrid wins [E1]." in seen["synth"]           # it saw the finished section
    assert sections[1][1] == "Adopt hybrid search first [E1]. An invented cite ."


def test_synthesis_without_any_findings_says_so_instead_of_inventing():
    plan = d.Plan("goal", "T", ["q"], [{"title": "R", "questions": [], "brief": "", "synthesis": True}])
    out = d.write_synthesis(plan.outline[0], plan, [("Findings", "*No supporting evidence was found.*")],
                            lambda p, json_mode=False: "should not be called")
    assert "No findings" in out


def test_preamble_variants_are_stripped():
    for pre in ("Here are the recommendations:", "Here is the section:", "Sure! Here you go.", "Certainly, below is it"):
        assert d._clean_prose(f"{pre}\n\nReal content [E1].", "Recs") == "Real content [E1]."


def test_plan_without_outline_gets_a_focused_second_call():
    calls = []

    def llm(prompt, json_mode=False):
        calls.append(prompt)
        if "Group these research sub-questions" in prompt:
            return json.dumps({"outline": [
                {"title": "Findings", "questions": [0, 1], "brief": ""},
                {"title": "Recommendations", "questions": [], "brief": ""}]})
        return json.dumps({"title": "T", "sub_questions": ["a?", "b?"]})   # no outline key

    plan = d.make_plan("goal", llm)
    assert len(calls) == 2
    assert [s["title"] for s in plan.outline] == ["Findings", "Recommendations"]
    assert plan.outline[-1]["synthesis"] is True


def test_plan_fallback_still_ends_with_a_synthesis_section():
    llm = lambda p, json_mode=False: json.dumps({"title": "T", "sub_questions": ["a?", "b?"]})  # noqa: E731
    plan = d.make_plan("goal", llm)           # the second call also returns no outline
    assert [s["questions"] for s in plan.outline] == [[0], [1], []]
    assert plan.outline[-1]["synthesis"] is True and plan.outline[-1]["title"] == "Practical recommendations"


def test_topic_extracted_from_revision_request():
    assert d._notes_topic("add a section on cost and operational effort") == "cost and operational effort"
    assert d._notes_topic("Please also include a section about privacy.") == "privacy"
    assert d._notes_intent("drop the history of RAG") == ("remove", "history of RAG")
    assert d._notes_intent("Please remove the section on cost") == ("remove", "cost")
    assert d._notes_intent("less theory") == ("remove", "theory")
    assert d._notes_intent("add AI safety") == ("add", "AI safety")


def test_ignored_revision_request_is_enforced_but_honored_ones_are_left_alone():
    llm_ignores = lambda p, json_mode=False: json.dumps({  # noqa: E731
        "title": "T", "sub_questions": ["a?", "b?"],
        "outline": [{"title": "Findings", "questions": [0, 1], "brief": ""},
                    {"title": "Recommendations", "questions": [], "brief": ""}]})
    plan = d.make_plan("goal", llm_ignores, notes="add a section on cost and operational effort")
    assert [s["title"] for s in plan.outline] == ["Findings", "Cost and operational effort", "Recommendations"]
    assert plan.sub_questions[-1] == "What does the library say about cost and operational effort?"
    assert plan.outline[1]["questions"] == [2] and plan.outline[-1]["synthesis"] is True

    llm_honors = lambda p, json_mode=False: json.dumps({  # noqa: E731
        "title": "T", "sub_questions": ["What are the cost and operational effort factors?", "b?"],
        "outline": [{"title": "Findings", "questions": [0, 1], "brief": ""},
                    {"title": "Recommendations", "questions": [], "brief": ""}]})
    plan2 = d.make_plan("goal", llm_honors, notes="add a section on cost and operational effort")
    assert len(plan2.outline) == 2 and len(plan2.sub_questions) == 2      # already covered, nothing added

    llm_partial = lambda p, json_mode=False: json.dumps({  # noqa: E731
        "title": "T", "sub_questions": ["What are the cost factors?", "b?"],
        "outline": [{"title": "Findings", "questions": [0, 1], "brief": ""},
                    {"title": "Recommendations", "questions": [], "brief": ""}]})
    plan3 = d.make_plan("goal", llm_partial, notes="add a section on cost and operational effort")
    assert len(plan3.outline) == 3                                          # one shared word is not enough


def test_feedback_is_saved_in_frontmatter_and_read_back_newest_first(tmp_path):
    import frontmatter

    from research_assistant import vault

    folder = tmp_path / "Research"
    folder.mkdir()
    for slug, title in (("a", "Report A"), ("b", "Report B"), ("c", "Unrated")):
        (folder / f"{slug}.md").write_text(frontmatter.dumps(frontmatter.Post("body", title=title, goal="g")), encoding="utf-8")
    import time

    vault.set_feedback(str(tmp_path), "Research", "a", "down", "too generic, no numbers")
    time.sleep(0.05)                         # Windows clock ticks ~15 ms; real feedback is seconds apart
    vault.set_feedback(str(tmp_path), "Research", "b", "up", "")
    got = vault.recent_feedback(str(tmp_path), "Research", n=5)
    assert [g["title"] for g in got] == ["Report B", "Report A"]         # newest first, unrated excluded
    assert got[1]["rating"] == "down" and got[1]["note"] == "too generic, no numbers"
    assert frontmatter.load(folder / "a.md").content == "body"            # report text untouched
    try:
        vault.set_feedback(str(tmp_path), "Research", "a", "meh")
        raise AssertionError("bad rating accepted")
    except ValueError:
        pass
    assert vault.recent_feedback(str(tmp_path / "nope"), "Research") == []


def test_lessons_reach_the_planner_prompt():
    seen = {}

    def llm(prompt, json_mode=False):
        seen["prompt"] = prompt
        return json.dumps({"title": "T", "sub_questions": ["a?", "b?"],
                           "outline": [{"title": "F", "questions": [0, 1], "brief": ""},
                                       {"title": "R", "questions": [], "brief": ""}]})

    lessons = d.format_lessons([{"title": "Old", "rating": "down", "note": "no numbers"},
                                {"title": "Good", "rating": "up", "note": ""}])
    d.make_plan("goal", llm, lessons=lessons)
    assert 'The report "Old" was NOT useful: no numbers' in seen["prompt"]
    assert 'The report "Good" was useful' in seen["prompt"]
    d.make_plan("goal", llm)                                              # no lessons -> no feedback paragraph
    assert "feedback on earlier reports" not in seen["prompt"]
