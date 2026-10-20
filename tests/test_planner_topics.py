"""E-019: the plan must cover every topic the goal names, and never turn qualifiers into catch-all questions."""
import json

from research_assistant import deep_report as d

GOAL = ("Building a private RAG system for a small team: which embedding models to use, how to chunk documents, hybrid "
        "keyword and vector search, reranking, how to evaluate retrieval and answer quality, and how to run the whole "
        "system locally on a single 8 GB GPU")
QUESTIONS = [
    "Which embedding models can run locally on an 8 GB GPU?",
    "How do chunking strategies for documents affect retrieval precision?",
    "What are the trade-offs of hybrid keyword and vector search?",
    "Which reranking models run locally and how much do they help?",
    "How can retrieval and answer quality be evaluated?",
    "What hardware and software does the whole system need on a single 8 GB GPU?",
]
TOPICS = ["Building a private RAG system", "for a small team", "how to chunk documents", "hybrid keyword and vector search",
          "reranking", "how to evaluate retrieval and answer quality"]


def fake(rejected=("chunk", "evaluat"), topics=TOPICS, questions=QUESTIONS, covered=()):
    asked = []

    def llm(prompt, json_mode=False):
        asked.append(prompt)
        if "research methodologist" in prompt:
            return json.dumps({"title": "Private RAG", "sub_questions": questions, "outline": [
                {"title": f"S{i}", "questions": [i], "brief": ""} for i in range(len(questions))] + [
                {"title": "Practical recommendations", "questions": [], "brief": ""}]})
        if "Is this question needed" in prompt:                  # the scope judge wrongly rejects two named topics
            return json.dumps({"needed": not any(w in prompt.split("One question")[1] for w in rejected)})
        if "List the distinct things" in prompt:
            return json.dumps({"topics": list(topics)})
        if "No question uses the words of this part of the goal" in prompt:
            topic = prompt.split('part of the goal: "')[1].split('"')[0]
            if topic in covered:
                return json.dumps({"covered": True})
            return json.dumps({"question": f"Which documented methods exist for {topic}?", "title": topic.title()})
        return "{}"
    return llm, asked


def test_P_T01_a_question_on_a_topic_the_goal_names_is_never_dropped_by_the_scope_judge():
    llm, _ = fake()
    plan = d.make_plan(GOAL, llm)
    assert any("chunk" in q for q in plan.sub_questions) and any("evaluat" in q for q in plan.sub_questions)
    assert plan.dropped == []


def test_P_T02_qualifiers_and_the_overall_subject_are_not_topics():
    llm, _ = fake()
    assert d.goal_topics(GOAL, llm) == ["how to chunk documents", "hybrid keyword and vector search", "reranking",
                                        "how to evaluate retrieval and answer quality"]
    plan = d.make_plan(GOAL, llm)
    assert not any("What does the evidence say" in q for q in plan.sub_questions)
    assert not any("small team" in s["title"].lower() for s in plan.outline)


def test_P_T03_a_really_missing_topic_gets_a_real_question_written_by_the_model():
    without_reranking = [q for q in QUESTIONS if "rerank" not in q]
    llm, _ = fake(questions=without_reranking, topics=TOPICS + ["how to version the index"])   # not in the goal: ignored
    plan = d.make_plan(GOAL, llm)
    assert "Which documented methods exist for reranking?" in plan.sub_questions
    assert any(s["title"] == "Reranking" for s in plan.outline)
    assert not any("version the index" in q for q in plan.sub_questions)
    assert plan.outline[-1].get("synthesis")                               # the synthesis section stays last


def test_P_T04_the_template_question_is_only_a_fallback_when_the_model_fails():
    question, title = d._question_for("how to version the index", GOAL, lambda p, json_mode=False: "not json")
    assert question == "What methods, settings and evidence are documented for how to version the index?"
    assert title == "How to version the index"


def test_P_T05_a_topic_an_existing_question_covers_in_other_words_is_not_added_again():
    topics = TOPICS + ["run the whole system locally"]                      # Q6 says "the entire pipeline": no word match
    llm, _ = fake(topics=topics, covered=("run the whole system locally",))
    plan = d.make_plan(GOAL, llm)
    assert len(plan.sub_questions) == len(QUESTIONS)                        # nothing added


def test_P_T06_a_leading_and_is_trimmed_from_a_topic():
    llm, _ = fake(topics=["and answer quality"])
    assert d.goal_topics(GOAL, llm) == ["answer quality"]
