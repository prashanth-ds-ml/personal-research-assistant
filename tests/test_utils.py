"""The quick assistant's helpers (previously untested)."""

import time

from research_assistant.utils import strip_thinking_tokens


def test_thinking_blocks_are_removed_and_the_answer_kept():
    assert strip_thinking_tokens("<think>hmm</think>The answer.") == "The answer."
    assert strip_thinking_tokens("A<think>x</think>B<think>y</think>C") == "ABC"
    assert strip_thinking_tokens("no tags here") == "no tags here"


def test_pathological_tag_orders_terminate_quickly_and_do_not_grow():
    # These made the old implementation loop forever / exhaust memory.
    start = time.time()
    for text in ("</think><think>", "a</think>b<think>c", "<think>", "</think>", "<think><think></think>",
                 "</think>" * 50 + "<think>" * 50):
        out = strip_thinking_tokens(text)
        assert len(out) <= len(text)
    assert time.time() - start < 1.0


def test_an_unclosed_opening_tag_leaves_the_text_alone():
    assert strip_thinking_tokens("Answer <think>never closed") == "Answer <think>never closed"


def test_a_stray_closing_tag_is_left_as_is():
    assert strip_thinking_tokens("oops</think> then text") == "oops</think> then text"
