"""v3 report checks from the 2026-10-19 review: citation repair, wording support, strict tables, extractive summary."""
from research_assistant import deep_report, desk
from research_assistant import report_checks as rc


def ev(eid, text, source="E5 paper"):
    return deep_report.Evidence(id=eid, claim=f"{source} › section", quote=text, source=source, heading="",
                                sub_questions=[0], passage=True)


# the real drift case: three neighbouring chunks of one paper, the sentence cites the wrong one
E7 = ev("E7", "We mine and assemble CCPairs, a large collection of text pairs from heterogeneous sources: (post, comment) pairs "
              "from Reddit, (question, upvoted answer) pairs from Stackexchange, and citation pairs from scientific papers.")
E8 = ev("E8", "In this work, we train a general-purpose text embedding model E5 from weak supervision signals with a simple "
              "contrastive training framework.")
E9 = ev("E9", "This paper presents E5, a family of state-of-the-art text embeddings that transfer well to a wide range of tasks.")
SECTION = [E7, E8, E9]


def test_V3_T01_a_citation_to_a_neighbouring_chunk_is_moved_to_the_chunk_that_says_it():
    stats: dict = {}
    text = ("Modern pipelines curate (post, comment) pairs from Reddit and (question, answer) pairs from Stackexchange [E8]. "
            "E5 transfers well to a wide range of tasks [E9].")
    out = rc.repair_citations(text, SECTION, stats)
    assert "Stackexchange [E7]." in out and "[E8]" not in out
    assert "tasks [E9]." in out                                             # a right citation is left alone
    assert stats == {"cited": 2, "repaired": 1}


def test_V3_T02_repair_needs_a_clearly_better_passage_and_leaves_tables_alone():
    weak = "Embeddings help many systems in practice [E8]."                 # no passage carries it: nothing to move to
    assert rc.repair_citations(weak, SECTION) == weak
    table = "| Pairs | Source |\n|---|---|\n| (post, comment) | Reddit [E8] |"
    assert rc.repair_citations(table, SECTION) == table


def test_V3_T03_a_cited_sentence_whose_words_are_not_in_the_cited_passage_is_flagged_in_v3_only():
    by_id = {e.id: e for e in SECTION}
    known = rc.evidence_numbers(SECTION)
    s = "Image models rely on convolutional networks converting pixel values [E9]."
    assert "[E9] [cited; wording not found in the cited evidence]." in rc.label_text(s, by_id, known, flags_only=True)
    assert rc.label_text(s, by_id, known).endswith("[single source]")      # v2 labels unchanged
    ok = "E5 is a family of text embeddings that transfer well to a wide range of tasks [E9]."
    assert rc.label_text(ok, by_id, known, flags_only=True) == ok


def test_V3_T04_tables_must_cite_every_row_and_carry_only_cited_numbers():
    evs = [ev("E14", "| embed-english-v3.0 | 128 | 05:32 | 1024 |", "Pinecone"), ev("E1", "BERT yields 12 vectors of dimension 768.")]
    deep_report.reset_stats()
    uncited = "Text before.\n\n| Model | Batch |\n|---|---|\n| embed-english-v3.0 | 128 |\n\nText after."
    assert "|" not in deep_report._strict_tables(uncited, evs)               # the 2026-10-19 speed table: no citations
    wrong_number = "| Model | Dim |\n|---|---|\n| BERT | 1024 [E1] |"
    assert "|" not in deep_report._strict_tables(wrong_number, evs)          # 1024 is not in E1
    good = "| Model | Dim |\n|---|---|\n| BERT | 768 [E1] |\n| embed-english-v3.0 | 1024 [E14] |"
    assert deep_report._strict_tables(good, evs) == good
    assert deep_report.snapshot_stats()["tables_dropped"] == 2


def test_V3_T05_the_summary_only_repeats_cited_section_sentences():
    plan = deep_report.Plan(goal="g", title="t", sub_questions=["q1", "q2"], outline=[
        {"title": "Data", "questions": [0]}, {"title": "Gaps", "questions": [1]},
        {"title": "Practical recommendations", "questions": [], "synthesis": True}])
    sections = [("Data", "| a | b |\n\nE5 is trained on CCPairs mined from Reddit and Stackexchange [E7]. More text [E8]."),
                ("Gaps", "*The library does not have enough evidence for this section.*"),
                ("Practical recommendations", "Start from a pretrained E5 checkpoint rather than from scratch [E8].")]
    out = deep_report.extractive_summary(plan, sections, ["Gaps"])
    assert out.startswith("**Recommendation:** Start from a pretrained E5 checkpoint rather than from scratch [E8].")
    assert "- **Data:** E5 is trained on CCPairs mined from Reddit and Stackexchange [E7]." in out
    assert "Gaps:" not in out and out.endswith("Evidence is thin or missing for: Gaps.")


def test_V3_T06_the_trace_reads_v3_flags_placed_before_the_full_stop():
    md = ("## Data\n\nE5 uses CCPairs from Reddit [E7] [cited; wording not found in the cited evidence]. "
          "It has 1024 dimensions [E8] [cited; figure not in the cited evidence].\n")
    rows = desk.report_sentences(md)
    assert [r["flag"] for r in rows] == ["wording", "figure"] and rows[1]["cites"] == ["E8"]
    assert "[cited;" not in rows[0]["text"] and rows[0]["text"].endswith("[E7].")


def test_V3_T07_a_section_gets_its_best_8_passages_best_first_and_the_rest_is_recorded():
    evs = [deep_report.Evidence(id=f"E{i}", claim=f"Doc {i} › s", quote=f"Passage number {i} about embeddings.",
                                source=f"Doc {i}", heading="", sub_questions=[0], passage=True, score=3 if i in (11, 12) else 2)
           for i in range(1, 13)]
    plan = deep_report.Plan(goal="g", title="t", sub_questions=["q"], outline=[{"title": "S", "questions": [0]}])
    seen = []
    deep_report.reset_stats()
    deep_report.write_section(plan.outline[0], plan, evs, lambda p, json_mode=False: seen.append(p) or "Text [E11].")
    prompt = seen[0]
    assert prompt.index("[E11]") < prompt.index("[E12]") < prompt.index("[E1]")              # the 3s first, then retrieval order
    assert "[E6]" in prompt and "[E7]" not in prompt and "[E10]" not in prompt                # 8 given: E11, E12, E1..E6
    assert deep_report.snapshot_stats()["passages_not_given"] == 4


def test_V3_T08_an_abbreviation_after_a_bracket_does_not_end_the_sentence():
    parts = rc._sentences("Use qwen3.5:9b-q4_K_M (approx. 6.6 GB VRAM) to stay within limits [E1]. Next sentence here.")
    assert len(parts) == 2 and parts[0].endswith("[E1].")
