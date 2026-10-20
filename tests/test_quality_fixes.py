"""2026-10-20 audit fixes: source authority, subject-bound relevance, no restating, passages wording."""
from research_assistant import collector, deep_report
from research_assistant import report_checks as rc
from research_assistant.authority import DOCS, PAPER, WEB, authority


def test_Q_T01_authority_paper_docs_web():
    assert authority("https://arxiv.org/abs/2212.03533") == PAPER
    assert authority("https://example.com/whitepaper.pdf") == PAPER
    assert authority("https://anything.org/x", kind="paper") == PAPER
    assert authority("https://docs.qdrant.tech/concepts/hybrid") == DOCS
    assert authority("https://huggingface.co/BAAI/bge-m3") == DOCS
    assert authority("https://medium.com/@someone/rag-guide") == WEB


def test_Q_T02_unattended_runs_take_papers_and_docs_one_grade_below_the_bar_and_rank_them_first_among_equals():
    cands = [{"id": "web3", "score": 3, "authority": WEB}, {"id": "paper2", "score": 2, "authority": PAPER},
             {"id": "web2", "score": 2, "authority": WEB}, {"id": "docs3", "score": 3, "authority": DOCS},
             {"id": "paper1", "score": 1, "authority": PAPER}]
    assert [d["id"] for d in collector.auto_select(cands, 3)] == ["docs3", "web3", "paper2"]


def test_Q_T03_the_relevance_grade_is_bound_to_the_component_the_question_names():
    assert "ONLY about a different component" in deep_report.RELEVANT_PROMPT
    assert "every part of the question" in deep_report.RELEVANT_PROMPT          # partial answers count (2026-10-20 re-grade)
    assert "whole system or pipeline, every component counts" in deep_report.RELEVANT_PROMPT


def test_Q_T04_a_restated_sentence_is_dropped_and_counted():
    stats: dict = {}
    text = ("The recommended configuration for the embedding engine is FP16 or Quantized Q8 [E4]. "
            "Hybrid search fuses keyword and vector results with reciprocal rank fusion [E12]. "
            "The embedding engine configuration recommends FP16 or Quantized Q8 for the engine [E4].")
    out = rc.drop_restated(text, stats)
    assert out.count("FP16") == 1 and "reciprocal rank fusion" in out and stats == {"restated": 1}
    different = "BM25 needs no GPU [E3]. Dense retrieval needs embeddings on a GPU or CPU [E3]."
    assert rc.drop_restated(different) == different                          # same citation, different point: kept


def test_Q_T05_with_equal_grades_a_section_gets_papers_before_web_pages():
    evs = [deep_report.Evidence(id="E1", claim="Blog › s", quote="blog passage about chunking", source="Blog", heading="",
                                sub_questions=[0], passage=True, score=2, url="https://someblog.dev/post", kind="web"),
           deep_report.Evidence(id="E2", claim="Paper › s", quote="paper passage about chunking", source="Paper", heading="",
                                sub_questions=[0], passage=True, score=2, url="https://arxiv.org/abs/1", kind="paper")]
    plan = deep_report.Plan(goal="g", title="t", sub_questions=["q"], outline=[{"title": "S", "questions": [0]}])
    seen = []
    deep_report.write_section(plan.outline[0], plan, evs, lambda p, json_mode=False: seen.append(p) or "Text [E2].")
    assert seen[0].index("[E2]") < seen[0].index("[E1]")


def test_Q_T06_the_v3_status_table_counts_passages():
    row = rc.status_table([{"title": "A", "facts": 3, "documents": 2, "status": "supported"}], rc.Standards(flags_only=True))
    assert row.startswith("| Section | Passages | Documents | Status |")
    assert rc.status_table([], rc.Standards()).startswith("| Section | Facts |")      # v2 reports unchanged


def test_Q_T07_the_ai_engineering_expert_sites_rank_with_official_docs():
    assert authority("https://lilianweng.github.io/posts/2023-06-23-agent/") == DOCS
    assert authority("https://docs.langchain.com/oss/python/langgraph/overview") == DOCS
    assert authority("https://langchain-ai.github.io/langgraph/") == DOCS
    assert collector.AI_SITES[0] == "sebastianraschka.com"                     # one list, shared with the collector


def test_Q_T08_a_domain_specific_source_must_be_named_as_such_in_the_sentence():
    med = deep_report.Evidence(id="E1", claim="Medical LLM › Eval", quote="Answers were judged for faithfulness by clinicians.",
                               source="Design and Evaluation of a Source-Grounded Medical LLM for Clinical Decision Support",
                               heading="", sub_questions=[0], passage=True)
    by_id, known = {"E1": med}, rc.evidence_numbers([med])
    general = rc.label_text("Answers should be judged for faithfulness by experts [E1].", by_id, known, flags_only=True)
    assert "[cited; domain not stated from the cited evidence]" in general
    named = "In a clinical decision-support study, answers were judged for faithfulness by clinicians [E1]."
    assert rc.label_text(named, by_id, known, flags_only=True) == named
    assert rc.source_domains([med]) == {"medical"}
    assert "name the domain in" in deep_report.PASSAGE_SECTION_PROMPT

