"""A model call that never stops must be cut off (a real run once sat 1.5 hours inside one)."""
import itertools

import pytest

from research_assistant import deep_report as d


def test_normal_stream_is_joined():
    assert d.consume(iter(["Hel", "lo ", "world"]), max_chars=100, deadline_s=10) == "Hello world"


def test_endless_newlines_are_stopped():
    with pytest.raises(d.RunawayGeneration, match="repeating"):
        d.consume(itertools.repeat("\n"), max_chars=10**9, deadline_s=10**9)


def test_repeated_phrase_is_stopped():
    with pytest.raises(d.RunawayGeneration, match="repeating"):
        d.consume(itertools.cycle(["the model repeats this ", "sentence again and again "]),
                  max_chars=10**9, deadline_s=10**9)


def test_endless_varied_text_hits_the_length_cap():
    words = (f"word{i} " for i in itertools.count())
    with pytest.raises(d.RunawayGeneration, match="characters"):
        d.consume(words, max_chars=5_000, deadline_s=10**9)


def test_deadline_applies_even_when_tokens_keep_arriving():
    ticks = itertools.count()

    def clock():
        return next(ticks) * 1.0                    # one fake second per look at the clock

    words = (f"w{i} " for i in itertools.count())
    with pytest.raises(d.RunawayGeneration, match="longer than"):
        d.consume(words, max_chars=10**9, deadline_s=50, clock=clock)


def test_stream_is_closed_when_stopped():
    closed = []

    def gen():
        try:
            while True:
                yield "\n"
        finally:
            closed.append(True)

    with pytest.raises(d.RunawayGeneration):
        d.consume(gen(), max_chars=10**9, deadline_s=10**9)
    assert closed == [True]                          # the server is told to stop generating


def test_resilient_retries_a_runaway_then_gives_up_without_crashing():
    d.reset_stats()
    attempts = []

    def raw(prompt, json_mode, attempt):
        attempts.append(attempt)
        raise d.RunawayGeneration("looping")

    llm = d.resilient(raw)
    assert llm("q", json_mode=True) == ""
    assert attempts == [0, 1, 2]
    assert d.snapshot_stats()["gave_up"] == 1


def test_a_retry_that_behaves_succeeds():
    d.reset_stats()

    def raw(prompt, json_mode, attempt):
        if attempt == 0:
            raise d.RunawayGeneration("looping")
        return '{"ok": true}'

    assert d.resilient(raw)("q", json_mode=True) == '{"ok": true}'
    assert d.snapshot_stats()["retries"] == 1


def test_ordinary_text_and_table_rules_are_not_mistaken_for_a_loop():
    assert not d._loops("| Method | Recall |\n|---|---|---|\n| BM25 | 0.68 |\n")
    assert not d._loops("The quick brown fox jumps over the lazy dog. " * 2)
    assert not d._loops("a" * 30)


# ---- Stop ----------------------------------------------------------------------------------------

def test_stop_is_noticed_while_a_call_is_generating():
    ticks = itertools.count()

    def clock():
        return next(ticks) * 1.0

    words = (f"w{i} " for i in itertools.count())
    with pytest.raises(d.RunStopped):
        d.consume(words, max_chars=10**9, deadline_s=10**9, clock=clock, should_stop=lambda: True)


def test_a_stopped_run_makes_no_further_model_calls_and_is_never_retried():
    d.reset_stats()
    called = []
    llm = d.resilient(lambda prompt, json_mode, attempt: called.append(attempt) or "x")
    d.set_stop_check(lambda: True)
    try:
        with pytest.raises(d.RunStopped):
            llm("q")
        assert called == []
    finally:
        d.set_stop_check(None)

    def raw(prompt, json_mode, attempt):
        called.append(attempt)
        raise d.RunStopped()

    with pytest.raises(d.RunStopped):
        d.resilient(raw)("q")
    assert called == [0]                                  # RunStopped is not retried
