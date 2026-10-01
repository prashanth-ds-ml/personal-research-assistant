"""Report quality stages 3-5: honest gap sections, one recommendation, no unlabelled invented numbers."""

import json

from research_assistant import deep_report as d
from research_assistant import report_checks as rc

STD = rc.Standards(min_facts=3, min_docs=2, min_share=0.5)


def ev(i, source, qs, claim=None, quote=None):
    return d.Evidence(id=f"E{i}", claim=claim or f"claim number {i}", quote=quote or f"quote text number {i} here",
                      source=source, heading="", sub_questions=qs)


def plan(sections, questions=("q0?", "q1?", "q2?", "q3?")):
    return d.Plan(goal="goal", title="T", sub_questions=list(questions), outline=sections)


EVIDENCE = [ev(1, "A", [0]), ev(2, "B", [0]), ev(3, "A", [0]),          # section 0: 3 facts, 2 documents: supported
            ev(4, "A", [1])]                                              # section 1: 1 fact: thin; section 2: nothing: gap

OUTLINE = [{"title": "Landscape", "questions": [0], "brief": "b"},
           {"title": "Tokenizers", "questions": [1], "brief": "b"},
           {"title": "Scaling", "questions": [2], "brief": "b"},
           {"title": "Recommendations", "questions": [], "brief": "r", "synthesis": True}]


class Recorder:
    """A fake model that records every prompt and answers by prompt type."""

    def __init__(self, recommendation="Continue pretraining an existing model.", summary="Summary says [E1].", same=True):
        self.prompts, self.recommendation, self.summary, self.same = [], recommendation, summary, same

    def __call__(self, prompt, json_mode=False):
        self.prompts.append(prompt)
        if "This is a synthesis section" in prompt:                 # (its first line is also "Write the report section")
            return "We recommend continuing pretraining an existing model [E1]."
        if "Write the report section" in prompt:
            title = prompt.split('"')[1]
            return f"Body of {title} [E1]."
        if "State its main recommendation" in prompt:
            return json.dumps({"recommendation": self.recommendation})
        if "recommend the same course of action" in prompt:
            return json.dumps({"same": self.same})
        return self.summary

    def saw(self, text):
        return any(text in p for p in self.prompts)


# ---- stage 3: support, gap notes, gap reports ----------------------------------------------------------

def test_section_support_statuses():
    sup = rc.plan_support(OUTLINE, EVIDENCE, STD)
    assert {i: s["status"] for i, s in sup.items()} == {0: "supported", 1: "thin", 2: "gap"}      # synthesis is not listed
    assert sup[0]["facts"] == 3 and sup[0]["documents"] == 2
    one_doc = [ev(i, "Same", [0]) for i in range(1, 6)]
    assert rc.section_support(OUTLINE[0], one_doc, STD)["status"] == "thin"       # five facts from ONE document is thin


def test_unsupported_sections_become_gap_notes_without_asking_the_model():
    llm = Recorder()
    sections = dict(d.write_all(plan(OUTLINE), EVIDENCE, llm, standards=rc.Standards(3, 2, 0.3)))
    assert sections["Landscape"].startswith("Body of Landscape")
    assert sections["Tokenizers"].startswith("*The library does not have enough evidence")
    assert "claim number 4 [E4]" in sections["Tokenizers"] and "q1" in sections["Tokenizers"]
    assert sections["Scaling"].startswith("*The library does not have enough evidence")
    assert "holds nothing relevant" in sections["Scaling"]
    assert not llm.saw('"Tokenizers"') and not llm.saw('"Scaling"')              # the model never wrote them


def test_the_recommendation_only_sees_supported_sections_and_is_told_what_is_missing():
    llm = Recorder()
    d.write_all(plan(OUTLINE), EVIDENCE, llm, standards=rc.Standards(3, 2, 0.3))
    synth = next(p for p in llm.prompts if "This is a synthesis section" in p)
    assert "Body of Landscape" in synth and "Body of Tokenizers" not in synth
    assert "NO usable evidence" in synth and "Tokenizers" in synth and "Scaling" in synth


def test_a_report_that_is_mostly_gaps_gives_no_recommendation():
    llm = Recorder()
    p = plan(OUTLINE)
    sections = d.write_all(p, EVIDENCE, llm, standards=STD)                       # 1 of 3 supported: under 50%
    assert sections[-1][1].startswith("*This report cannot give a recommendation")
    assert not llm.saw("This is a synthesis section")
    report = d.assemble(p, sections, EVIDENCE, llm, standards=STD)
    assert "## Evidence status" in report and "| Landscape | 3 | 2 | supported |" in report
    assert "| Scaling | 0 | 0 | no evidence found |" in report
    summary = report.split("## Executive summary")[1].split("## Landscape")[0]
    assert "does not hold enough evidence" in summary and "gives no recommendation" in summary
    assert not llm.saw("executive summary")                                        # the summary is not model-written
    assert "evidence section(s) did not have enough evidence" in report            # and Limitations say so


def test_a_report_with_enough_evidence_is_written_normally():
    full = [ev(i, "A" if i % 2 else "B", [q]) for q in range(3) for i in range(q * 3 + 1, q * 3 + 4)]
    sections = d.write_all(plan(OUTLINE), full, Recorder(), standards=STD)
    assert all(not rc.is_generated(b) for _, b in sections)
    assert sections[-1][1].startswith("We recommend")


# ---- stage 4: one recommendation, no repeats, no filler -------------------------------------------------

def _assemble(llm, standards=STD):
    full = [ev(i, "A" if i % 2 else "B", [0]) for i in range(1, 7)]
    p = plan([{"title": "Findings", "questions": [0], "brief": "b"},
              {"title": "Recommendations", "questions": [], "brief": "r", "synthesis": True}], ("q0?",))
    sections = [("Findings", "Findings text [E1]."), ("Recommendations", "We recommend continuing pretraining [E2].")]
    return d.assemble(p, sections, full, llm, standards=standards)


def test_the_summary_is_told_the_recommendation_and_checked_against_it():
    llm = Recorder(same=True)
    report = _assemble(llm)
    assert llm.saw("The recommendation of this report is: Continue pretraining an existing model.")
    assert "Summary says" in report and "may not state the same recommendation" not in report


def test_a_contradicting_summary_is_rewritten_once_then_flagged():
    flip = Recorder(same=False)
    report = _assemble(flip)
    assert len([p for p in flip.prompts if "previous summary contradicted" in p]) == 1     # rewritten once, not in a loop
    assert "may not state the same recommendation" in report                               # still different: say so


def test_a_rewrite_that_fixes_the_contradiction_raises_no_alarm():
    answers = iter([False, True])
    base = Recorder()

    def llm(prompt, json_mode=False):
        if "recommend the same course of action" in prompt:
            return json.dumps({"same": next(answers)})
        return base(prompt, json_mode)

    assert "may not state the same recommendation" not in _assemble(llm)


def test_no_recommendation_in_the_section_means_no_consistency_alarm():
    llm = Recorder(recommendation="", same=False)
    assert "may not state the same recommendation" not in _assemble(llm)
    assert not llm.saw("recommend the same course of action")


def test_repeated_paragraphs_are_dropped_but_tables_lists_and_short_text_are_kept():
    para = "Hybrid retrieval combines keyword and vector search to improve recall on real document collections today."
    table = "| a | b |\n|---|---|\n| 1 | 2 |"
    out = dict(rc.dedupe_sections([("One", f"{para}\n\n{table}\n\nShort line."),
                                   ("Two", f"{para} [E3]\n\n{table}\n\nShort line.\n\n- item one\n\n- item one")]))
    assert para in out["One"]
    assert para not in out["Two"].replace("[E3]", "")                               # the repeat is gone
    assert table in out["Two"] and "Short line." in out["Two"] and out["Two"].count("- item one") == 2


def test_filler_sentences_are_removed():
    text = ("The goal of this section is to explore tokenizers. Fertility is 2.1 tokens per word [E1]. "
            "Further research is needed. In this section we discuss costs.\n\n| a | b |\n|---|---|\n| The goal of this | x |")
    out = rc.strip_filler(text)
    assert out.startswith("Fertility is 2.1 tokens per word [E1].")
    assert "goal of this section" not in out and "Further research" not in out and "In this section" not in out
    assert "| The goal of this | x |" in out                                        # table rows are never edited


# ---- stage 5: labels and invented numbers --------------------------------------------------------------

BY_ID = {"E1": ev(1, "A", [0], claim="Fertility is 2.1 tokens per word", quote="fertility of 2.1 tokens per word"),
         "E2": ev(2, "B", [0], claim="Vocabulary size is 32000", quote="a vocabulary of 32000 entries"),
         "E3": ev(3, "A", [0])}
KNOWN = rc.evidence_numbers(list(BY_ID.values()))


def test_every_sentence_gets_a_label_from_its_citations():
    out = rc.label_text("Two sources agree [E1][E2]. One source says so [E3]. This follows from the above. "
                        "It costs 15000 dollars overall.", BY_ID, KNOWN)
    assert "Two sources agree [E1][E2]. [established]" in out
    assert "One source says so [E3]. [single source]" in out
    assert "This follows from the above. [inference]" in out
    assert "It costs 15000 dollars overall. [inference: figures not from sources]" in out


def test_numbers_in_the_evidence_are_not_flagged_and_small_numbers_are_ignored():
    out = rc.label_text("Fertility around 2.1 matters here. A vocabulary of 32000 is common. We used 3 sections.", BY_ID, KNOWN)
    assert "[inference: figures not from sources]" not in out and out.count("[inference]") == 3


def test_tables_headings_quotes_and_abbreviations_are_handled():
    text = ("# Heading 99999\n| a | 123456 |\n> quoted 777777\n"
            "See e.g. the survey [E1] for more detail. Another sentence is here [E2].")
    out = rc.label_text(text, BY_ID, KNOWN)
    assert out.split("\n")[0] == "# Heading 99999" and "| a | 123456 |" in out and "> quoted 777777" in out
    assert "e.g. the survey [E1] for more detail. [single source]" in out            # not split after "e.g."
    assert "Another sentence is here [E2]. [single source]" in out


def test_the_invented_cost_line_from_the_real_report_is_flagged():
    body = "Pretraining from scratch: 100-200 GPU-hours, $10,000-$20,000 for a 4B model."
    assert "[inference: figures not from sources]" in rc.label_text(body, BY_ID, KNOWN)


def test_labels_can_be_switched_off_and_generated_notes_are_never_labelled():
    p = plan([{"title": "Findings", "questions": [0], "brief": "b"}], ("q0?",))
    full = [ev(i, "A" if i % 2 else "B", [0]) for i in range(1, 7)]
    sentence = "Plain sentence about things [E1]."
    off = d.assemble(p, [("Findings", sentence)], full, Recorder(), standards=rc.Standards(3, 2, 0.5, claim_labels=False))
    assert "[single source]" not in off and "[established]" not in off
    on = d.assemble(p, [("Findings", sentence)], full, Recorder(), standards=STD)
    assert f"{sentence} [single source]" in on
    sections = d.write_all(plan(OUTLINE), EVIDENCE, Recorder(), standards=STD)
    gap = d.assemble(plan(OUTLINE), sections, EVIDENCE, Recorder(), standards=STD)
    assert "To fill this gap, collect sources about: q2." in gap and "q2. [inference]" not in gap
