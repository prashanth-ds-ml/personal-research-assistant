"""A section the model failed to write is reported as failed, not 'supported', and does not get a made-up summary."""

import itertools

import pytest

from research_assistant import deep_report as d
from research_assistant import report_checks as rc

STD = rc.Standards(3, 2, 0.5)


def ev(i, source, q):
    return d.Evidence(id=f"E{i}", claim=f"claim {i}", quote=f"quote text {i} here", source=source, heading="", sub_questions=[q])


def test_failed_sections_are_marked_failed_summarised_by_code_and_their_facts_are_listed():
    plan = d.Plan("g", "T", ["q0?", "q1?"], [{"title": "A", "questions": [0]}, {"title": "B", "questions": [1]}])
    evidence = [ev(i, "X" if i % 2 else "Y", q) for q in (0, 1) for i in range(q * 3 + 1, q * 3 + 4)]
    failed = "*The model failed to write this section; the supporting evidence is listed in the appendix."
    asked = []
    report = d.assemble(plan, [("A", failed), ("B", failed)], evidence,
                        lambda p, json_mode=False: asked.append(p) or "never used", standards=STD)
    assert "| A | 3 | 2 | writing failed" in report and "| B | 3 | 2 | writing failed" in report
    assert "The model failed to write 2 of 2 sections" in report and "free memory" in report
    assert asked == []                                              # no model-written summary of nothing
    assert "[inference]" not in report.split("## A")[1].split("## Limitations")[0]   # the notes are not 'claims'
    assert "| E1 |" in report and "| E6 |" in report              # the facts the notes point to are in the appendix


def test_one_failed_section_among_good_ones_keeps_the_normal_summary():
    plan = d.Plan("g", "T", ["q0?", "q1?", "q2?"], [{"title": "A", "questions": [0]}, {"title": "B", "questions": [1]},
                                                    {"title": "C", "questions": [2]}])
    evidence = [ev(i, "X" if i % 2 else "Y", q) for q in (0, 1, 2) for i in range(q * 3 + 1, q * 3 + 4)]
    failed = "*The model failed to write this section; the supporting evidence is listed in the appendix."
    report = d.assemble(plan, [("A", "Good text about things [E1]."), ("B", failed), ("C", "More good text here [E7].")],
                        evidence, lambda p, json_mode=False: "Summary text here [E1].", standards=STD)
    assert "| B | 3 | 2 | writing failed" in report and "| A | 3 | 2 | supported" in report
    assert "Summary text here" in report


def test_placeholder_notes_are_never_labelled_or_deduplicated_away():
    for note in ("*The model failed to write this section; x.*", "*No findings were available to synthesise recommendations from.*",
                 "*No supporting evidence was found in the knowledge base for this section.*"):
        assert rc.is_generated(note)


# ---- the time limit: prose gets longer than JSON, and a timeout is not retried -------------------------------------

def test_a_deadline_is_its_own_error_and_is_not_retried():
    d.reset_stats()
    ticks = itertools.count()

    def clock():
        return next(ticks) * 1.0

    words = (f"w{i} " for i in itertools.count())
    with pytest.raises(d.DeadlineExceeded):
        d.consume(words, max_chars=10**9, deadline_s=30, clock=clock)
    attempts = []

    def raw(prompt, json_mode, attempt):
        attempts.append(attempt)
        raise d.DeadlineExceeded("too slow")

    assert d.resilient(raw)("q") == ""
    assert attempts == [0] and d.snapshot_stats()["gave_up"] == 1


def test_prose_may_take_much_longer_than_a_json_judgement():
    assert d.TEXT_DEADLINE >= 4 * d.CALL_DEADLINE
