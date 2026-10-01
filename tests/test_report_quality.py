"""Report quality, stages 0-2: archived-page filtering, off-topic facts, and the coverage check."""

import json

from langchain_core.embeddings import Embeddings
from langchain_core.runnables import RunnableConfig

from research_assistant import deep_report as d
from research_assistant import goal_graph
from research_assistant import graph as quick
from research_assistant import knowledge as k
from research_assistant.configuration import Configuration
from research_assistant.state import SummaryState


class Emb(Embeddings):
    def _e(self, t):
        t = t.lower()
        v = [float(t.count(w)) for w in ("hybrid", "tokenizer", "recall")]
        return v if any(v) else [0.001] * 3

    def embed_documents(self, texts):
        return [self._e(t) for t in texts]

    def embed_query(self, text):
        return self._e(text)


# ---- stage 0: archived local-document copies are left out, real web pages stay ---------------------------

def _kb(tmp_path):
    kb = k.KnowledgeBase(tmp_path / "kb.sqlite", Emb())
    kb.ingest_text("Library/paper.pdf", "# Paper\n\nThe hybrid tokenizer improves recall a lot in our tests here.\n")
    kb.ingest_text("Sources/q/web.md", "---\nsource: web\nurl: https://a.example/p\n---\n# Web\n\nThe hybrid tokenizer recall "
                                       "is high on this page of text for the web.\n")
    kb.ingest_text("Sources/q/local.md", "---\nurl: doc://runbook.md/p1\n---\n# Runbook\n\nThe hybrid tokenizer recall copy "
                                         "of a local document, archived by the quick assistant.\n")
    return kb


def test_search_can_skip_documents(tmp_path):
    kb = _kb(tmp_path)
    all_paths = {h["path"] for h in kb.search("hybrid tokenizer recall", k=10)}
    assert all_paths == {"Library/paper.pdf", "Sources/q/web.md", "Sources/q/local.md"}
    kept = kb.search("hybrid tokenizer recall", k=10, skip=lambda path, kind: kind == "document")
    assert {h["path"] for h in kept} == {"Library/paper.pdf", "Sources/q/web.md"}


def test_deep_research_skips_archived_copies_of_local_documents_but_keeps_web_pages(tmp_path):
    kb = _kb(tmp_path)
    cfg = Configuration()
    paths = {h["path"] for h in goal_graph.library_search(kb, cfg, k=10)("hybrid tokenizer recall")}
    assert paths == {"Library/paper.pdf", "Sources/q/web.md"}
    cfg.include_archived_pages = True
    paths = {h["path"] for h in goal_graph.library_search(kb, cfg, k=10)("hybrid tokenizer recall")}
    assert "Sources/q/local.md" in paths


def test_the_quick_assistant_does_not_archive_pages_from_local_documents(monkeypatch, tmp_path):
    monkeypatch.setattr(quick, "local_docs_search", lambda *a, **kw: {"results": [
        {"title": "Runbook", "url": "doc://runbook.md/p1", "content": "text", "raw_content": "text"}]})
    called = []
    monkeypatch.setattr(quick.vault, "archive_sources", lambda **kw: called.append(kw) or [{"path": "x"}])
    config: RunnableConfig = {"configurable": {"search_api": "local_docs", "vault_path": str(tmp_path)}}
    out = quick.web_research(SummaryState(search_query="q", research_topic="t"), config)
    assert called == [] and out["archived_sources"] == []


# ---- stage 1: true but off-topic facts are not evidence -----------------------------------------------

PASSAGE = "BERT-large has 213 million parameters. Qwen3-8B reaches 0.78 recall on the tool-calling benchmark."


def _llm(on_topic_for: dict, supported=True):
    """Extraction returns two facts; the judge says which are on topic (by the claim's first word)."""
    def llm(prompt, json_mode=False):
        if "directly support" in prompt:
            claim = prompt.split("Claim: ")[1].split("\n")[0]
            flag = on_topic_for.get(claim.split()[0], True)
            return json.dumps({"supported": supported, "on_topic": flag})
        return json.dumps({"facts": [
            {"claim": "BERT-large has 213 million parameters", "quote": "BERT-large has 213 million parameters"},
            {"claim": "Qwen3-8B reaches 0.78 recall", "quote": "Qwen3-8B reaches 0.78 recall on the tool-calling benchmark"}]})
    return llm


def test_off_topic_facts_are_dropped_and_counted():
    d.reset_stats()
    facts = d.extract_facts("How good are 4B-8B models at tool calling?", {"title": "T", "text": PASSAGE},
                            _llm({"BERT-large": False}))
    assert [f["claim"] for f in facts] == ["Qwen3-8B reaches 0.78 recall"]
    assert d.snapshot_stats()["off_topic"] == 1


def test_the_question_is_in_the_judging_prompt():
    seen = []

    def llm(prompt, json_mode=False):
        seen.append(prompt)
        return json.dumps({"supported": True, "on_topic": True})

    d._judge("claim", "quote", "passage", llm, question="Which tokenizer fits Telugu?")
    assert "Which tokenizer fits Telugu?" in seen[0] and "on_topic" in seen[0]
    d._judge("claim", "quote", "passage", llm)                      # no question: the topic line is simply absent
    assert "research question is" not in seen[1]


def test_a_missing_on_topic_answer_keeps_the_fact_and_unsupported_facts_are_still_dropped():
    d.reset_stats()
    keep = lambda prompt, json_mode=False: (json.dumps({"supported": True}) if "directly support" in prompt  # noqa: E731
                                            else _llm({})(prompt, json_mode))
    assert len(d.extract_facts("q", {"title": "T", "text": PASSAGE}, keep)) == 2
    assert d.extract_facts("q", {"title": "T", "text": PASSAGE}, _llm({}, supported=False)) == []
    assert d.snapshot_stats()["off_topic"] == 0                          # unsupported is not counted as off topic


def test_the_old_entailment_helper_still_works_for_the_scripts():
    llm = lambda prompt, json_mode=False: json.dumps({"supported": True, "on_topic": False})  # noqa: E731
    assert d._entailed("c", "q", "p", llm) is True                        # supported only; the scripts ignore topic


# ---- stage 2: coverage of each question ----------------------------------------------------------------

def _plan(n=3):
    return d.Plan(goal="g", title="T", sub_questions=[f"question {i}" for i in range(n)],
                  outline=[{"title": "S", "questions": list(range(n))}])


def test_coverage_marks_each_question_answered_thin_or_nothing():
    relevant_docs = {"question 0": 3, "question 1": 1, "question 2": 0}     # how many of the 4 passages are on topic

    def search(q):
        return [{"title": f"{q} doc {i}", "path": f"{q}-{i}", "text": f"{'RELEVANT ' if i < relevant_docs[q] else ''}text {i} of {q}"}
                for i in range(4)]

    def llm(prompt, json_mode=False):
        passage = prompt.split("<passage>")[1]
        return json.dumps({"relevant": "RELEVANT" in passage})

    rows = d.coverage(_plan(), search, llm)
    assert [r["status"] for r in rows] == ["answered", "thin", "nothing"]
    assert [r["relevant"] for r in rows] == [3, 1, 0] and rows[0]["index"] == 0 and rows[2]["checked"] == 4
    assert len(rows[0]["titles"]) == 3 and rows[2]["titles"] == []


def test_coverage_judges_documents_not_repeated_passages_from_one_document():
    def search(q):                                   # five passages, all from the same document
        return [{"title": "One doc", "path": "same", "text": f"RELEVANT passage {i}"} for i in range(5)]

    llm = lambda prompt, json_mode=False: json.dumps({"relevant": True})  # noqa: E731
    row = d.coverage(_plan(1), search, llm)[0]
    assert row["checked"] == 1 and row["status"] == "thin"          # one document is thin, however many passages it has


def test_an_unreadable_judgement_counts_as_not_relevant():
    search = lambda q: [{"title": "D", "path": "p", "text": "text"}]  # noqa: E731
    assert d.coverage(_plan(1), search, lambda prompt, json_mode=False: "not json")[0]["status"] == "nothing"
