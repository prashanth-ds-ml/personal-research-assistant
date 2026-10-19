"""The chunk size is locked (2026-10-19, Test A): every chunk respects the limits, and a library refuses to mix chunkers."""
import pytest
from langchain_core.embeddings import Embeddings

from research_assistant import knowledge


class Emb(Embeddings):
    def __init__(self):
        self.calls = []

    def embed_documents(self, texts):
        self.calls.append(len(texts))
        return [[1.0, float(len(t) % 7), 0.5] for t in texts]

    def embed_query(self, text):
        return [1.0, 0.0, 0.5]


def test_K_T01_a_huge_table_header_cannot_push_pieces_over_the_limit():
    header = "| " + " | ".join(f"column {i} " + "x" * 60 for i in range(35)) + " |"     # ~2,300 characters, as in TransMI
    rule = "|" + "---|" * 35
    rows = [f"| row {r} " + "| v " * 34 + "|" for r in range(40)]
    pieces = knowledge._split_table([header, rule, *rows], knowledge.MAX_TABLE_CHARS)
    assert len(pieces) > 1
    assert all(len(p) <= knowledge.MAX_TABLE_CHARS for p in pieces)
    assert all(p.splitlines()[1] == rule for p in pieces)                                     # header kept in each piece


def test_K_T02_a_new_library_records_the_chunker_and_refuses_another(tmp_path):
    kb = knowledge.KnowledgeBase(tmp_path / "kb.sqlite", Emb())
    assert kb._meta("chunker") == knowledge.CHUNKER
    kb.ingest_text("a.md", "# A\n\nSome text about embeddings.", title="A")
    kb.close()
    con = knowledge.sqlite3.connect(tmp_path / "kb.sqlite")
    con.execute("UPDATE meta SET value='v1 text=1200 table=2000' WHERE key='chunker'")
    con.commit()
    con.close()
    with pytest.raises(knowledge.ChunkerMismatch, match="reindex.py --rebuild"):
        knowledge.KnowledgeBase(tmp_path / "kb.sqlite", Emb())


def test_K_T03_rebuild_records_the_chunker_on_an_old_library(tmp_path):
    kb = knowledge.KnowledgeBase(tmp_path / "kb.sqlite", Emb())
    kb.ingest_text("a.md", "# A\n\nSome text about embeddings.", title="A")
    kb.db.execute("DELETE FROM meta WHERE key='chunker'")                                     # an old library: no record
    kb.db.commit()
    kb.rebuild()
    assert kb._meta("chunker") == knowledge.CHUNKER


def test_K_T04_embedding_goes_in_batches(tmp_path):
    emb = Emb()
    kb = knowledge.KnowledgeBase(tmp_path / "kb.sqlite", emb)
    md = "\n\n".join(f"## Part {i}\n\n" + ("word " * 300) for i in range(80))                 # many chunks in one document
    kb.ingest_text("big.md", md, title="Big")
    assert max(emb.calls) <= knowledge.EMBED_BATCH and sum(emb.calls) == kb.stats()["chunks"]


def test_K_T05_a_broken_giant_heading_is_capped_in_every_chunk():
    md = "# " + "Broken heading text " * 120 + "\n\nThe body of the section is short."
    (chunk,) = knowledge.chunk_markdown(md)
    assert len(chunk["heading"]) <= knowledge.MAX_HEADING_CHARS + 4 and chunk["heading"].endswith(" ...")
    assert len(chunk["text"]) < 400
