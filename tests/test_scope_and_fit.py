"""The report must stay on the user's goal: no drift from library titles, questions the goal does not need are dropped,
facts are judged against the whole goal, options become questions plus a decision, and filler is cut."""
import json

from research_assistant import deep_report as dr
from research_assistant import goal_graph


def _plan(questions, outline):
    return dr.Plan(goal="Build a text-only small model. Clarifications: no speech.", title="T", sub_questions=questions, outline=outline)


OUTLINE = [
    {"title": "Reasoning", "questions": [0, 1], "brief": "", "synthesis": False},
    {"title": "Speech", "questions": [2], "brief": "", "synthesis": False},
    {"title": "Deployment", "questions": [3, 4], "brief": "", "synthesis": False},
    {"title": "Recommendations", "questions": [], "brief": "", "synthesis": True},
]
QUESTIONS = ["How do small models reason?", "How is tool calling trained?", "How to fine-tune Wav2Vec2 for speech-to-text?",
             "How to deploy privately?", "What hardware does an 8B model need?"]


def _judge_llm(not_needed: set[str]):
    def llm(prompt, json_mode=False, **kw):
        needed = not any(q in prompt for q in not_needed)
        return json.dumps({"needed": needed, "reason": "x"})
    return llm


def test_clarifying_questions_no_longer_see_the_library_and_must_stay_on_the_goal():
    assert "{library}" not in goal_graph.CLARIFY_PROMPT
    assert "NEVER bring in a topic" in goal_graph.CLARIFY_PROMPT


def test_a_plan_question_that_is_not_part_of_the_goal_is_dropped_and_the_outline_is_remapped():
    plan = dr.scope_filter(_plan(QUESTIONS, OUTLINE), "goal", _judge_llm({"Wav2Vec2"}))
    assert "Wav2Vec2" not in " ".join(plan.sub_questions) and len(plan.sub_questions) == 4
    assert plan.dropped == [QUESTIONS[2]]
    titles = [s["title"] for s in plan.outline]
    assert "Speech" not in titles                                  # a section with nothing left disappears
    assert titles[-1] == "Recommendations" and plan.outline[-1]["synthesis"]   # the synthesis stays, last
    covered = sorted(i for s in plan.outline for i in s["questions"])
    assert covered == [0, 1, 2, 3]                                 # indexes point at the new list, with no gaps


def test_scope_filter_never_removes_on_a_model_error_and_keeps_a_minimum():
    def broken(prompt, json_mode=False, **kw):
        raise RuntimeError("model down")

    assert len(dr.scope_filter(_plan(QUESTIONS, OUTLINE), "g", broken).sub_questions) == 5
    # everything judged "not needed" would leave fewer than the minimum: the plan is left alone
    assert len(dr.scope_filter(_plan(QUESTIONS, OUTLINE), "g", _judge_llm(set(QUESTIONS))).sub_questions) == 5


def test_make_plan_applies_the_scope_check():
    def llm(prompt, json_mode=False, **kw):
        if "research methodologist" in prompt:
            return json.dumps({"title": "T", "sub_questions": QUESTIONS, "outline": OUTLINE[:3] + [{"title": "Recommendations", "questions": [], "brief": ""}]})
        return json.dumps({"needed": "Wav2Vec2" not in prompt})

    plan = dr.make_plan("Text-only small model", llm)
    assert plan.dropped == [QUESTIONS[2]] and len(plan.sub_questions) == 4


def test_the_plan_prompt_turns_alternatives_into_questions_and_a_decision():
    p = dr.PLAN_PROMPT
    assert "names alternatives" in p and "DECISION" in p
    assert "do NOT need or want" in p


def test_facts_are_judged_against_the_whole_goal_not_only_the_question():
    seen = []

    def llm(prompt, json_mode=False, **kw):
        seen.append(prompt)
        return json.dumps({"supported": True, "on_topic": True})

    dr._judge("claim", "quote", "passage", llm, question="Q?", goal="Build a text-only 8B model")
    assert "overall goal" in seen[0] and "text-only 8B model" in seen[0]
    seen.clear()
    dr._judge("claim", "quote", "passage", llm, question="Q?")          # no goal: unchanged behaviour
    assert "overall goal" not in seen[0]


def test_recommendations_must_fit_the_kind_of_system_the_goal_asks_about():
    s = dr.SYNTH_PROMPT
    assert "SAME kind of system" in s and "do not transfer" in s and "which to choose" in s


def test_filler_sentences_are_cut_but_cited_ones_stay():
    text = ("EoTD turns reasoning into equations [E3]. A comparison of the observed characteristics reveals specific patterns "
            "of limitation. The following table lists the models.\n\n"
            "A comparison of the key results shows a gain of 4 points [E5].")
    out = dr._drop_filler_sentences(text)
    assert "EoTD turns reasoning into equations [E3]." in out
    assert "reveals specific patterns" not in out and "following table" not in out
    assert "shows a gain of 4 points [E5]" in out                      # it carries a citation: kept


def test_a_table_that_only_repeats_the_prose_is_dropped_but_a_new_one_stays():
    prose = ("The CosmicFish-HRM model frequently halts before reaching the maximum reasoning budget [E1]. "
             "Its reasoning depth is highly input-dependent [E2].\n\n")
    repeat = ("| Subject | Observation | Evidence ID |\n| --- | --- | --- |\n"
              "| CosmicFish-HRM | Frequently halts before reaching the maximum reasoning budget | [E1] |\n"
              "| CosmicFish-HRM | Its reasoning depth is highly input-dependent | [E2] |")
    assert "| Subject" not in dr._drop_restating_tables(prose + repeat)
    new = ("| Model | Recall@10 | MRR |\n| --- | --- | --- |\n| Dense-only retrieval baseline system | 78% | 0.68 [E5] |\n"
           "| Hybrid search with reranking stage | 91% | 0.84 [E5] |")
    assert "| Model" in dr._drop_restating_tables(prose + new)


def test_the_model_sees_the_users_answers_but_not_the_assistants_questions():
    goal = ("Build a small model.\n\nClarifications from the user:\n"
            "Any hate speech detection requirements?\n  -> no speech capability yet only text\n"
            "Which audience?\n  -> developers\nRegion: India")
    seen = dr.model_goal(goal)
    assert "speech capability" in seen                # the user's own words are kept ...
    assert "hate speech detection requirements" not in seen and "Which audience?" not in seen   # ... the assistant's questions are not
    assert "- developers" in seen and "- Region: India" in seen      # a plain "key: value" statement is the user's too
    assert dr.model_goal("Just a goal") == "Just a goal"
    assert dr.model_goal("G\n\nClarifications from the user:\nQ1?\n  ->") == "G"       # nothing was answered


def test_a_plan_whose_questions_come_back_as_objects_is_still_used():
    def llm(prompt, json_mode=False, **kw):
        if "research methodologist" in prompt:
            return json.dumps({"title": "T", "sub_questions": [{"question": "What is A?"}, {"question": "What is B?"}, {"text": "What is C?"}],
                               "outline": [{"title": "S", "questions": [0, 1, 2], "brief": ""}, {"title": "R", "questions": [], "brief": ""}]})
        return json.dumps({"needed": True})

    assert dr.make_plan("goal", llm).sub_questions == ["What is A?", "What is B?", "What is C?"]


def test_a_goal_topic_with_no_question_gets_one_before_the_synthesis():
    base = _plan(QUESTIONS[:4], [
        {"title": "Reasoning", "questions": [0, 1], "brief": "", "synthesis": False},
        {"title": "Deployment", "questions": [2, 3], "brief": "", "synthesis": False},
        {"title": "Recommendations", "questions": [], "brief": "", "synthesis": True}])
    goal = "Build a model with strong reasoning and multilingual evaluation benchmarks.\n\nThe user also said (x):\n- no speech capability"

    def llm(prompt, json_mode=False, **kw):
        return json.dumps({"topics": ["reasoning",                   # already covered by the first question
                                      "multilingual evaluation benchmarks",   # no question mentions it
                                      "speech capability",           # only in the user's answer: not the goal sentence
                                      "something the goal never said"]})

    out = dr.add_missing_topics(base, goal, llm)
    assert len(out.sub_questions) == 5 and "multilingual evaluation benchmarks" in out.sub_questions[4]     # only the missing, grounded one
    assert [s["title"] for s in out.outline] == ["Reasoning", "Deployment", "Multilingual evaluation benchmarks", "Recommendations"]
    assert out.outline[2]["questions"] == [4] and out.outline[-1]["synthesis"]
    # nothing missing, or a model error: the plan is returned unchanged
    assert dr.add_missing_topics(base, goal, lambda p, json_mode=False, **kw: json.dumps({"topics": []})) is base

    def boom(prompt, json_mode=False, **kw):
        raise RuntimeError("down")

    assert dr.add_missing_topics(base, goal, boom) is base
