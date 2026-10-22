"""Offline tests for the knowledge base and deep-report pipeline (fake embeddings + fake LLM)."""

import json

from langchain_core.embeddings import Embeddings

from research_assistant import deep_report, knowledge


class KeywordEmbeddings(Embeddings):
    KEYWORDS = ["retrieval", "chunk", "rerank", "postgres", "cooking", "table"]

    def _e(self, t):
        t = t.lower()
        v = [float(t.count(k)) for k in self.KEYWORDS]
        return v if any(v) else [0.001] * len(self.KEYWORDS)

    def embed_documents(self, texts):
        return [self._e(t) for t in texts]

    def embed_query(self, text):
        return self._e(text)


MD = """# Guide

## Chunking
Chunk size matters. Smaller chunk sizes improve precision of retrieval.

## Results
| Method | Recall |
|---|---|
| BM25 | 0.61 |
| Hybrid | 0.78 |

## Kitchen
Cooking pasta takes ten minutes and a lot of salt.
"""


def test_chunker_keeps_tables_whole_and_prefixes_headings():
    chunks = knowledge.chunk_markdown(MD)
    tables = [c for c in chunks if c["kind"] == "table"]
    assert len(tables) == 1 and "Hybrid | 0.78" in tables[0]["text"] and "BM25" in tables[0]["text"]
    assert tables[0]["text"].startswith("[Guide > Results]")
    assert any(c["text"].startswith("[Guide > Chunking]") for c in chunks)


def test_hybrid_search_finds_keyword_and_semantic(tmp_path):
    kb = knowledge.KnowledgeBase(tmp_path / "kb.sqlite", KeywordEmbeddings())
    kb.ingest_text("a.md", MD, title="A")
    kb.ingest_text("b.md", "Postgres stores rows. Redis stores keys.", title="B")
    top = kb.search("what chunk size is best for retrieval", k=2)
    assert top[0]["title"] == "A" and "Chunk" in top[0]["text"]
    # exact rare token: only BM25 can find it (embedding has no dimension for it)
    assert kb.search("pasta", k=1)[0]["title"] == "A"


def test_ingest_is_incremental_and_prunes(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.md").write_text(MD)
    (docs / "b.txt").write_text("Postgres notes here.")
    kb = knowledge.KnowledgeBase(tmp_path / "kb.sqlite", KeywordEmbeddings())
    s1 = kb.ingest_folder(docs)
    assert s1["added"] == 2 and s1["unchanged"] == 0
    s2 = kb.ingest_folder(docs)
    assert s2["added"] == 0 and s2["unchanged"] == 2
    (docs / "a.md").write_text(MD + "\n## New\nRerank with a cross-encoder.")
    (docs / "b.txt").unlink()
    s3 = kb.ingest_folder(docs)
    assert s3["added"] == 1 and s3["removed"] == 1
    assert kb.stats()["documents"] == 1
    assert kb.search("cross-encoder rerank", k=1)[0]["path"] == "docs/a.md"
    assert kb.search("Postgres", k=3) == [] or all(h["path"] != "b.txt" for h in kb.search("Postgres", k=3))


def test_extract_drops_unverified_quotes():
    hit = {"title": "Doc", "text": "Hybrid retrieval reached 0.78 recall, beating BM25 at 0.61.", "heading": ""}
    good = "Hybrid retrieval reached 0.78 recall"
    llm = lambda p, json_mode=False: json.dumps({"supported": True}) if "directly support" in p else json.dumps({"facts": [  # noqa: E731
        {"claim": "Hybrid beats BM25", "quote": good},
        {"claim": "Invented", "quote": "Reranking doubled accuracy overnight"},
        {"claim": "Too short", "quote": "0.78"},
    ]})
    facts = deep_report.extract_facts("q", hit, llm)
    assert [f["claim"] for f in facts] == ["Hybrid beats BM25"]


def test_pipeline_end_to_end_with_fake_llm():
    hit = {"title": "Guide", "heading": "Results",
           "text": "Hybrid retrieval reached 0.78 recall, beating BM25 at 0.61."}

    def llm(prompt, json_mode=False):
        if "research methodologist" in prompt:
            return json.dumps({"title": "RAG report", "sub_questions": ["Does hybrid help?", "Unanswerable?"],
                               "outline": [{"title": "Hybrid", "questions": [0], "brief": "b"},
                                           {"title": "Gaps", "questions": [1], "brief": "b"}]})
        if "directly support" in prompt:
            return json.dumps({"supported": True})
        if "Extract facts" in prompt:
            if "Does hybrid help" in prompt:
                return json.dumps({"facts": [{"claim": "Hybrid beats BM25",
                                              "quote": "Hybrid retrieval reached 0.78 recall"}]})
            return json.dumps({"facts": []})
        if "Write the report section" in prompt:
            return "Hybrid wins [E1]. Invented cite [E99]."
        return "Summary [E1]."

    def search(q):
        return [hit] if "hybrid" in q.lower() else []

    report, stats = deep_report.run("Should we use hybrid?", search, llm, llm, llm, on_progress=lambda s: None,
                                    standards=deep_report.rc.Standards(1, 1, 0.0))
    assert stats["evidence"] == 1
    assert "[E99]" not in report and "Hybrid wins [E1]" in report
    assert "does not have enough evidence for this section" in report     # the unanswerable section says what is missing
    assert "holds nothing relevant" in report
    assert "| E1 | Hybrid beats BM25 |" in report        # appendix row for the cited fact
    assert "Thin evidence" in report


def test_entailment_check_drops_claims_the_quote_does_not_support():
    hit = {"title": "Doc", "text": "GPT-3 reached 92.5 accuracy on ReCoRD in the few-shot setting.", "heading": ""}
    quote = "GPT-3 reached 92.5 accuracy on ReCoRD"

    def llm(prompt, json_mode=False):
        if "directly support" in prompt:  # strict judge rejects the claim about "local models"
            return json.dumps({"supported": "local" not in prompt.lower()})
        return json.dumps({"facts": [{"claim": "Local models reached 92.5 on ReCoRD", "quote": quote},
                                     {"claim": "GPT-3 reached 92.5 accuracy on ReCoRD", "quote": quote}]})

    facts = deep_report.extract_facts("q", hit, llm)
    assert [f["claim"] for f in facts] == ["GPT-3 reached 92.5 accuracy on ReCoRD"]


def test_plan_assigns_each_question_to_one_section_and_no_orphans():
    llm = lambda p, json_mode=False: json.dumps({  # noqa: E731
        "title": "T", "sub_questions": ["a?", "b?", "c?"],
        "outline": [{"title": "S1", "questions": [0, 1], "brief": ""},
                    {"title": "S2", "questions": [1], "brief": ""}]})
    plan = deep_report.make_plan("goal", llm)
    assigned = [i for sec in plan.outline for i in sec["questions"]]
    assert sorted(assigned) == [0, 1, 2] and len(assigned) == len(set(assigned))


def test_duplicate_evidence_is_merged_and_prose_cleaned():
    hit = {"title": "Doc", "heading": "", "text": "Hybrid search reached 0.78 recall. Hybrid retrieval got 0.78 recall too."}
    llm = lambda p, json_mode=False: json.dumps({"facts": [  # noqa: E731
        {"claim": "Hybrid search reached 0.78 recall", "quote": "Hybrid search reached 0.78 recall"},
        {"claim": "Hybrid search reached 0.78 recall.", "quote": "Hybrid retrieval got 0.78 recall too"}]}
    ) if "Extract facts" in p else json.dumps({"supported": True})
    plan = deep_report.Plan("g", "t", ["q"], [{"title": "S", "questions": [0], "brief": ""}])
    ev = deep_report.gather_evidence(plan, lambda q: [hit], llm)
    assert len(ev) == 1
    cleaned = deep_report._clean_prose("Here is the section:\n**Background**\nReal text [E1].", "Background")
    assert cleaned == "Real text [E1]."


def test_citation_ranges_are_expanded_and_validated():
    assert deep_report._expand_citation_ranges("A [E6–E9]. B [E3, E5]. C [E2-4].") == \
        "A [E6][E7][E8][E9]. B [E3][E5]. C [E2][E3][E4]."


def test_ungrounded_tables_are_dropped_grounded_kept():
    grounded = "Claim [E1].\n\n| a | b |\n|---|---|\n| x | 1 |\n"
    assert "| x | 1 |" in deep_report._drop_unsupported_tables(grounded)
    cited_rows = "Text.\n\n| a | b |\n|---|---|\n| x | 1 [E2] |\n"
    assert "[E2]" in deep_report._drop_unsupported_tables(cited_rows)
    padded = "No cites.\n\n| a | b |\n|---|---|\n| x | 1 |\n\nAfter."
    out = deep_report._drop_unsupported_tables(padded)
    assert "|" not in out and "After." in out


def test_retrieve_caps_chunks_per_document_and_fuses_queries():
    def hit(doc, n):
        return {"title": doc, "path": doc, "text": f"{doc} passage {n} " * 5, "heading": ""}

    def search(q):  # one document floods the results for the plain question
        return [hit("A", i) for i in range(6)] if "variant" not in q else [hit("B", 0), hit("C", 0)]

    llm = lambda p, json_mode=False: json.dumps({"queries": ["variant one", "variant two"]})  # noqa: E731
    out = deep_report.retrieve("plain question", search, llm, k=8, per_doc=3)
    docs = [h["path"] for h in out]
    assert docs.count("A") == 3 and "B" in docs and "C" in docs
    # without an LLM it degrades to the single query, still capped
    assert [h["path"] for h in deep_report.retrieve("plain question", search, None, per_doc=2)] == ["A", "A"]


def test_title_comes_from_first_heading():
    md = "## Attention Is All You Need\n\nAuthors...\n"
    assert knowledge.title_from_markdown(md, "fallback") == "Attention Is All You Need"
    assert knowledge.title_from_markdown("no heading here", "fallback") == "fallback"


def test_reference_sections_are_not_indexed():
    md = "# Paper\n\n## Method\nWe use hybrid retrieval.\n\n## References\n[1] Someone. A paper. 2020.\n\n## Acknowledgments\nThanks."
    heads = [c["heading"] for c in knowledge.chunk_markdown(md)]
    assert heads == ["Paper > Method"]


def test_resilient_retries_then_recovers_and_never_raises():
    attempts = []

    def flaky(prompt, json_mode, attempt):
        attempts.append(attempt)
        if attempt < 2:
            raise RuntimeError("prediction aborted, token repeat limit reached")
        return "ok"

    assert deep_report.resilient(flaky)("p") == "ok" and attempts == [0, 1, 2]

    def dead(prompt, json_mode, attempt):
        raise RuntimeError("connection refused")

    before = deep_report.LLM_STATS["gave_up"]
    assert deep_report.resilient(dead)("p") == ""          # degrades, does not crash
    assert deep_report.LLM_STATS["gave_up"] == before + 1
    # and an empty generation yields an empty extraction / a placeholder section, not an exception
    hit = {"title": "T", "text": "some passage text here", "heading": ""}
    assert deep_report.extract_facts("q", hit, lambda p, json_mode=False: "") == []
    sec = {"title": "S", "questions": [0], "brief": ""}
    ev = [deep_report.Evidence("E1", "c", "quote text here", "T", "", [0])]
    plan = deep_report.Plan("g", "t", ["q"], [sec])
    assert "failed to write" in deep_report.write_section(sec, plan, ev, lambda p, json_mode=False: "")


def test_faithfulness_scoring_math():
    import importlib.util
    import pathlib

    spec = importlib.util.spec_from_file_location(
        "score_faithfulness", pathlib.Path(__file__).parent.parent / "evals" / "scripts" / "score_faithfulness.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    rows = ([{"judge": "y", "human": "y"}] * 6 + [{"judge": "y", "human": "n"}] * 2
            + [{"judge": "n", "human": "n"}] * 3 + [{"judge": "n", "human": "y"}] * 1 + [{"judge": "y", "human": ""}])
    s = mod.score(rows)
    assert s["labeled"] == 12 and s["false_accepts"] == 2 and s["false_rejects"] == 1
    assert abs(s["precision_of_accepted"] - 0.75) < 1e-9 and abs(s["recall_of_supported"] - 6 / 7) < 1e-9


def test_ingesting_a_second_folder_does_not_delete_the_first(tmp_path):
    lib, vaultdir = tmp_path / "library", tmp_path / "sources"
    lib.mkdir()
    vaultdir.mkdir()
    (lib / "paper.md").write_text("# Paper\n\nHybrid retrieval beats BM25 on recall.")
    (vaultdir / "page.md").write_text("# Page\n\nPostgres notes about tables.")
    kb = knowledge.KnowledgeBase(tmp_path / "kb.sqlite", KeywordEmbeddings())
    kb.ingest_folder(lib)
    kb.ingest_folder(vaultdir)
    assert kb.stats()["documents"] == 2            # the old code would have pruned the library here
    (vaultdir / "page.md").unlink()
    s = kb.ingest_folder(vaultdir)
    assert s["removed"] == 1 and kb.stats()["documents"] == 1
    assert kb.search("hybrid retrieval", k=1)[0]["path"] == "library/paper.md"


class _FakeDoc:
    def __init__(self, md, pages):
        self._md, self.pages = md, pages

    def export_to_markdown(self):
        return self._md


class _FakeConv:
    def __init__(self, md, pages, log, flag):
        self.md, self.pages, self.log, self.flag = md, pages, log, flag

    def convert(self, path):
        self.log.append(self.flag)
        return type("R", (), {"document": _FakeDoc(self.md, self.pages)})()


def test_ocr_is_skipped_for_born_digital_and_used_for_scans(tmp_path):
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF")
    log = []
    born_digital = lambda ocr: _FakeConv("word " * 400, [1, 2], log, ocr)  # noqa: E731
    assert knowledge.convert_with_ocr_fallback(pdf, born_digital).startswith("word")
    assert log == [False]                                   # OCR never ran

    log.clear()
    scanned = lambda ocr: _FakeConv("OCR TEXT " * 100 if ocr else "", [1, 2, 3], log, ocr)  # noqa: E731
    assert "OCR TEXT" in knowledge.convert_with_ocr_fallback(pdf, scanned)
    assert log == [False, True]                             # empty without OCR -> retried with OCR


def test_remove_drops_one_document_and_its_chunks(tmp_path):
    kb = knowledge.KnowledgeBase(tmp_path / "kb.sqlite", KeywordEmbeddings())
    kb.ingest_text("Library/a.md", MD, title="A")
    kb.ingest_text("Library/b.md", MD + "\nExtra retrieval notes about reranking.", title="B")
    before = kb.stats()
    assert kb.remove("Library/a.md") is True
    assert kb.remove("Library/a.md") is False          # already gone
    assert kb.remove("nope.md") is False
    after = kb.stats()
    assert after["documents"] == before["documents"] - 1
    assert all(hit["path"] != "Library/a.md" for hit in kb.search("chunk size", k=10))
    kb.close()
