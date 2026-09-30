"""Knowledge-base robustness: the defects from the 2026-09-30 audit (chunk sizes, embedding-model safety,
transactions, recorded failures, cache invalidation, closing)."""

import sqlite3

import pytest
from langchain_core.embeddings import Embeddings

from research_assistant import goal_graph, knowledge
from research_assistant.knowledge import (
    EmbeddingMismatch,
    KnowledgeBase,
    chunk_markdown,
)


class Emb(Embeddings):
    """Bag-of-keywords embedding with a chosen dimension (extra dimensions are constant)."""

    KEYWORDS = ["retrieval", "recall", "reranking", "table", "pasta", "postgres", "alpha", "beta"]

    def __init__(self, dim=8, fail=False):
        self.dim, self.fail = dim, fail

    def _e(self, t):
        t = t.lower()
        v = [float(t.count(k)) for k in self.KEYWORDS[: self.dim]] + [0.5] * max(self.dim - len(self.KEYWORDS), 0)
        return v if any(v) else [0.001] * self.dim

    def embed_documents(self, texts):
        if self.fail:
            raise ConnectionError("Ollama is down")
        return [self._e(t) for t in texts]

    def embed_query(self, text):
        return self._e(text)


BODY = "Hybrid retrieval improves recall on real corpora, as measured in several studies. "


# ---- chunking -------------------------------------------------------------------------

def test_a_huge_table_is_split_by_rows_with_its_header_repeated_and_loses_no_rows():
    rows = ["| Method | Recall | Setting |", "|---|---|---|"] + [f"| method-{i} | 0.{i % 10}{i % 7} | setting {i} |" for i in range(600)]
    md = "# Results\n\n" + "\n".join(rows)
    chunks = [c for c in chunk_markdown(md) if c["kind"] == "table"]
    assert len(chunks) > 5 and max(len(c["text"]) for c in chunks) < knowledge.MAX_TABLE_CHARS + 300
    body = "\n".join(c["text"] for c in chunks)
    assert all(f"| method-{i} |" in body for i in range(600))                 # nothing lost
    assert all("| Method | Recall | Setting |" in c["text"] and "|---|---|---|" in c["text"] for c in chunks)


def test_a_small_table_stays_in_one_chunk():
    md = "# R\n\n| A | B |\n|---|---|\n| 1 | 2 |\n| 3 | 4 |"
    assert [c["kind"] for c in chunk_markdown(md)] == ["table"]


def test_captions_are_dropped_beside_real_content_but_a_short_note_is_kept():
    doc = f"# Paper\n\n## Intro\n{BODY}\n\n## Fig\nFigure 2: Overview\n"
    assert not any("Figure 2" in c["text"] for c in chunk_markdown(doc))
    assert len(chunk_markdown("# Note\n\nShort note.")) == 1


def test_only_real_reference_sections_are_skipped():
    md = (f"# P\n\n## Cross-references in practice\n{BODY}\n\n## 7 References\n[1] A. Author. 2020. Title of a paper.\n\n"
          f"## Acknowledgments\nThanks to everyone who helped us.\n\n## Related work\n{BODY}")
    heads = [c["heading"] for c in chunk_markdown(md)]
    assert heads == ["P > Cross-references in practice", "P > Related work"]


def test_page_numbers_follow_the_page_markers():
    md = f"<!-- page 1 -->\n{BODY}\n<!-- page 2 -->\n{BODY} second page\n<!-- page 3 -->\n{BODY} third page"
    assert [c["page"] for c in chunk_markdown(md)] == [1, 2, 3]


# ---- embedding model safety -----------------------------------------------------------

def test_opening_a_library_with_a_different_embedding_model_is_refused(tmp_path):
    path = tmp_path / "kb.sqlite"
    with KnowledgeBase(path, Emb(), embedding_model="ollama:model-a") as kb:
        kb.ingest_text("a.md", f"# A\n\n{BODY}")
    with pytest.raises(EmbeddingMismatch, match="model-a"):
        KnowledgeBase(path, Emb(), embedding_model="ollama:model-b")
    KnowledgeBase(path, Emb(), embedding_model="ollama:model-a").close()     # the same model still opens


def test_a_model_with_a_different_vector_size_cannot_write_into_the_library(tmp_path):
    kb = KnowledgeBase(tmp_path / "kb.sqlite", Emb(dim=8))
    kb.ingest_text("a.md", f"# A\n\n{BODY}")
    kb2 = KnowledgeBase(tmp_path / "kb.sqlite", Emb(dim=5))                   # no model name: the size check still guards
    with pytest.raises(EmbeddingMismatch, match="5-number vectors"):
        kb2.ingest_text("b.md", f"# B\n\n{BODY} reranking")
    with pytest.raises(EmbeddingMismatch, match="embedding model has changed"):
        kb2.search("hybrid recall")
    assert kb.stats()["documents"] == 1                                       # nothing half-written


def test_a_legacy_library_with_no_recorded_model_adopts_the_configured_one(tmp_path):
    path = tmp_path / "kb.sqlite"
    KnowledgeBase(path, Emb()).ingest_text("a.md", f"# A\n\n{BODY}")          # built before the model was recorded
    with KnowledgeBase(path, Emb(), embedding_model="ollama:model-a") as kb:
        assert kb._meta("embedding_model") == "ollama:model-a"
    with pytest.raises(EmbeddingMismatch):
        KnowledgeBase(path, Emb(), embedding_model="ollama:model-b")


def test_rebuild_reembeds_from_saved_text_without_the_source_files(tmp_path):
    path = tmp_path / "kb.sqlite"
    old = KnowledgeBase(path, Emb(dim=8), embedding_model="ollama:model-a")
    old.ingest_text("a.md", f"# A\n\n{BODY} reranking")
    old.close()
    kb = KnowledgeBase(path, Emb(dim=5))                                      # new model, opened without the name check
    result = kb.rebuild(embedding_model="ollama:model-b")
    assert result == {"rebuilt": 1, "missing_markdown": []}
    assert kb.search("reranking recall", k=1)[0]["path"] == "a.md"
    with pytest.raises(EmbeddingMismatch):
        KnowledgeBase(path, Emb(dim=5), embedding_model="ollama:model-a")
    KnowledgeBase(path, Emb(dim=5), embedding_model="ollama:model-b").close()


def test_rebuild_refuses_to_guess_when_a_document_has_no_saved_text(tmp_path):
    kb = KnowledgeBase(tmp_path / "kb.sqlite", Emb())
    kb.ingest_text("a.md", f"# A\n\n{BODY}")
    kb.db.execute("UPDATE docs SET markdown = NULL")                          # how a pre-upgrade document looks
    kb.db.commit()
    with pytest.raises(EmbeddingMismatch, match="cannot be rebuilt"):
        kb.rebuild()


def test_an_old_database_without_the_new_columns_is_upgraded_in_place(tmp_path):
    path = tmp_path / "old.sqlite"
    db = sqlite3.connect(path)
    db.executescript("CREATE TABLE docs (id INTEGER PRIMARY KEY, path TEXT UNIQUE, hash TEXT, title TEXT, "
                     "source_url TEXT, ingested_at TEXT, n_chunks INTEGER);")
    db.commit()
    db.close()
    kb = KnowledgeBase(path, Emb())
    cols = {r[1] for r in kb.db.execute("PRAGMA table_info(docs)")}
    assert {"status", "error", "markdown"} <= cols


# ---- transactions ---------------------------------------------------------------------

def test_a_failed_embedding_never_costs_you_the_previous_version_of_a_document(tmp_path):
    emb = Emb()
    kb = KnowledgeBase(tmp_path / "kb.sqlite", emb)
    kb.ingest_text("a.md", f"# A\n\nAlpha {BODY}")
    emb.fail = True
    with pytest.raises(ConnectionError):
        kb.ingest_text("a.md", f"# A\n\nBeta {BODY} changed")                 # changed content, embedding fails
    emb.fail = False
    assert kb.stats()["documents"] == 1
    assert "Alpha" in kb.search("alpha", k=1)[0]["text"]                      # the old version is intact
    assert kb.ingest_text("a.md", f"# A\n\nBeta {BODY} changed") > 0           # and the retry works


# ---- failures are remembered (no re-converting a broken PDF on every run) ------------------

def test_a_file_that_fails_to_convert_is_not_converted_again_until_it_changes(tmp_path, monkeypatch):
    calls = []

    def converter(path):
        calls.append(path.name)
        raise RuntimeError("corrupt pdf")

    monkeypatch.setattr(knowledge, "convert_to_markdown", converter)
    root = tmp_path / "docs"
    root.mkdir()
    f = root / "broken.pdf"
    f.write_bytes(b"%PDF-broken")
    kb = KnowledgeBase(tmp_path / "kb.sqlite", Emb())

    s1 = kb.ingest_folder(root)
    s2 = kb.ingest_folder(root)
    assert len(calls) == 1                                                    # converted once, not at every run
    assert "corrupt pdf" in s1["failed"][0] and "could not be converted earlier" in s2["failed"][0]
    f.write_bytes(b"%PDF-fixed-version")                                      # the file changes: worth another try
    kb.ingest_folder(root)
    assert len(calls) == 2
    assert kb.stats()["unreadable"] == 1 and kb.stats()["documents"] == 0


def test_a_file_with_no_usable_text_is_recorded_as_empty_and_not_reconverted(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(knowledge, "convert_to_markdown", lambda p: calls.append(1) or "")
    root = tmp_path / "docs"
    root.mkdir()
    (root / "scan.pdf").write_bytes(b"%PDF-scanned")
    kb = KnowledgeBase(tmp_path / "kb.sqlite", Emb())
    assert kb.ingest_folder(root)["empty"] == 1
    assert kb.ingest_folder(root)["empty"] == 1 and len(calls) == 1


def test_an_embedding_outage_is_retried_next_time_not_remembered_as_a_failure(tmp_path):
    emb = Emb(fail=True)
    root = tmp_path / "docs"
    root.mkdir()
    (root / "a.md").write_text(f"# A\n\n{BODY}")
    kb = KnowledgeBase(tmp_path / "kb.sqlite", emb)
    assert "Ollama is down" in kb.ingest_folder(root)["failed"][0]
    emb.fail = False
    assert kb.ingest_folder(root)["added"] == 1


# ---- folders and converted copies ---------------------------------------------------------

def test_folders_with_the_same_name_get_distinct_namespaces_and_do_not_prune_each_other(tmp_path):
    a, b = tmp_path / "x" / "Papers", tmp_path / "y" / "Papers"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    (a / "one.md").write_text(f"# One\n\nAlpha {BODY}")
    (b / "two.md").write_text(f"# Two\n\nBeta {BODY}")
    ns = goal_graph.folder_namespaces([a, b])
    assert len(set(ns.values())) == 2 and all(v.startswith("Papers-") for v in ns.values())
    kb = KnowledgeBase(tmp_path / "kb.sqlite", Emb())
    kb.ingest_folder(a, namespace=ns[a.resolve()])
    kb.ingest_folder(b, namespace=ns[b.resolve()])
    assert kb.stats()["documents"] == 2                                        # the second did not prune the first
    assert goal_graph.folder_namespaces([a, a]) == {a.resolve(): "Papers"}      # the same folder twice is no clash


def test_converted_copies_must_go_outside_the_indexed_folder_and_keep_their_structure(tmp_path):
    root = tmp_path / "docs"
    (root / "sub").mkdir(parents=True)
    (root / "a.md").write_text(f"# A\n\nAlpha {BODY}")
    (root / "sub" / "a.md").write_text(f"# A2\n\nBeta {BODY}")                  # same file name in another folder
    kb = KnowledgeBase(tmp_path / "kb.sqlite", Emb())
    with pytest.raises(ValueError, match="inside the folder being indexed"):
        kb.ingest_folder(root, md_out=root / "converted")
    out = tmp_path / "converted"
    kb.ingest_folder(root, md_out=out)
    assert (out / "a.md").exists() and (out / "sub" / "a.md").exists()         # no flattening, no overwrite
    assert "Alpha" in (out / "a.md").read_text() and "Beta" in (out / "sub" / "a.md").read_text()


# ---- concurrency and lifecycle --------------------------------------------------------------

def test_a_second_connection_sees_changes_and_the_first_never_crashes_on_deleted_rows(tmp_path):
    path = tmp_path / "kb.sqlite"
    a, b = KnowledgeBase(path, Emb()), KnowledgeBase(path, Emb())
    a.ingest_text("one.md", f"# One\n\nAlpha {BODY}")
    assert a.search("alpha recall", k=3)                                       # a caches its matrix
    b.ingest_text("two.md", f"# Two\n\nBeta pasta {BODY}")                     # another connection writes
    assert any(h["path"] == "two.md" for h in a.search("beta pasta", k=3))     # a notices (generation changed)
    b.ingest_folder(tmp_path / "empty-namespace", namespace="zzz") if (tmp_path / "empty-namespace").exists() else None
    with b.db:
        b._delete_doc(b.db.execute("SELECT id FROM docs WHERE path='one.md'").fetchone()[0])
        b._bump_generation()
    assert all(h["path"] != "one.md" for h in a.search("alpha recall", k=5))   # no TypeError on a vanished row


def test_context_manager_closes_the_connection(tmp_path):
    with KnowledgeBase(tmp_path / "kb.sqlite", Emb()) as kb:
        kb.ingest_text("a.md", f"# A\n\n{BODY}")
    with pytest.raises(sqlite3.ProgrammingError):
        kb.db.execute("SELECT 1")


def test_stats_separate_searchable_documents_from_unreadable_ones(tmp_path):
    kb = KnowledgeBase(tmp_path / "kb.sqlite", Emb())
    kb.ingest_text("a.md", f"# A\n\n{BODY}")
    kb.ingest_text("bad.pdf", "", status="failed", error="boom")
    assert kb.stats() == {"documents": 1, "chunks": 1, "unreadable": 1}
