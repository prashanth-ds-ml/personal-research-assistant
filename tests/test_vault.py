"""Automated versions of the reliability checks in EVALS.md.

All offline: no Ollama, no network. Retrieval uses a deterministic fake
embedding model so the test checks the plumbing (chunking, ranking, formatting),
not embedding quality.
"""

import frontmatter
import pytest
from langchain_core.embeddings import Embeddings

from research_assistant import vault


class KeywordEmbeddings(Embeddings):
    """Bag-of-keywords embedding: one dimension per keyword, so cosine
    similarity tracks keyword overlap deterministically."""

    KEYWORDS = ["retrieval", "rag", "context", "postgres", "redis", "cooking"]

    def _embed(self, text: str) -> list[float]:
        t = text.lower()
        vec = [float(t.count(k)) for k in self.KEYWORDS]
        return vec if any(vec) else [0.001] * len(self.KEYWORDS)

    def embed_documents(self, texts):
        return [self._embed(t) for t in texts]

    def embed_query(self, text):
        return self._embed(text)


# ---- 1. source archive ------------------------------------------------------

def test_archive_writes_frontmatter_and_full_content(tmp_path):
    results = {"results": [{
        "url": "https://www.example.com/post",
        "title": "Example Post",
        "content": "short snippet",
        "raw_content": "FULL PAGE TEXT",
    }]}
    archived = vault.archive_sources(
        str(tmp_path), "Sources", "topic", "2026-09-28", "q1", "duckduckgo", results
    )
    assert len(archived) == 1
    post = frontmatter.load(archived[0]["file_path"])
    assert post["url"] == "https://www.example.com/post"
    assert post["query"] == "q1"
    assert "fetched_at" in post.metadata
    assert post.content.strip() == "FULL PAGE TEXT"


def test_archive_stubs_binary_sources(tmp_path):
    results = {"results": [
        {"url": "https://x.com/paper.pdf", "title": "Paper", "content": "snip", "raw_content": "%PDF junk"},
        {"url": "https://x.com/page", "title": "Corrupt", "content": "snip2", "raw_content": "�" * 20},
    ]}
    archived = vault.archive_sources(
        str(tmp_path), "Sources", "t", "2026-09-28", "q", "duckduckgo", results
    )
    for a in archived:
        body = frontmatter.load(a["file_path"]).content
        assert "full content not archived" in body
        assert "junk" not in body


def test_archive_indexes_continue_across_loops(tmp_path):
    r = {"results": [{"url": "https://a.com", "title": "A", "content": "c"}]}
    first = vault.archive_sources(str(tmp_path), "Sources", "t", "d", "q1", "x", r)
    second = vault.archive_sources(str(tmp_path), "Sources", "t", "d", "q2", "x", r)
    assert first[0]["index"] == 1 and second[0]["index"] == 2
    assert first[0]["file_path"] != second[0]["file_path"]


def test_archive_noop_without_vault():
    assert vault.archive_sources("", "Sources", "t", "d", "q", "x", {"results": [{}]}) == []


# ---- report writing ---------------------------------------------------------

def test_report_links_resolve_and_filenames_dont_collide(tmp_path):
    r = {"results": [{"url": "https://a.com", "title": "A", "content": "c"}]}
    archived = vault.archive_sources(str(tmp_path), "Sources", "t", "2026-09-28", "q", "x", r)
    args = (str(tmp_path), "Research", "Sources", "2026-09-28", "t", "Topic", "## Key Findings\nx", archived, 1)
    p1 = vault.write_report(*args)
    p2 = vault.write_report(*args)
    assert p1 != p2 and p2.endswith("-2.md")

    body = frontmatter.load(p1).content
    link = body.split("](")[1].split(")")[0]
    assert ((tmp_path / "Research" / link).resolve()).exists()


def test_report_falls_back_when_no_sources(tmp_path):
    p = vault.write_report(str(tmp_path), "Research", "Sources", "d", "t", "T", "body", [], 0)
    assert "No sources archived" in frontmatter.load(p).content


# ---- 2. vault-as-context ----------------------------------------------------

@pytest.fixture
def fake_embeddings(monkeypatch):
    import langchain.embeddings as emb
    monkeypatch.setattr(emb, "init_embeddings", lambda name: KeywordEmbeddings())


def _note(tmp_path, name, title, body):
    d = tmp_path / "Research"
    d.mkdir(exist_ok=True)
    (d / name).write_text(frontmatter.dumps(frontmatter.Post(body, title=title)), encoding="utf-8")


def test_retrieval_surfaces_related_note_first(tmp_path, fake_embeddings):
    _note(tmp_path, "rag.md", "What is RAG?", "retrieval augmented generation rag retrieval")
    _note(tmp_path, "cook.md", "Pasta", "cooking cooking recipes")
    out = vault.retrieve_vault_context(str(tmp_path), "Research", "fake", "context and rag", top_k=1)
    assert "What is RAG?" in out and "rag.md" in out
    assert "Pasta" not in out


def test_retrieval_empty_vault_returns_empty(tmp_path, fake_embeddings):
    assert vault.retrieve_vault_context(str(tmp_path), "Research", "fake", "anything", 3) == ""
    assert vault.retrieve_vault_context("", "Research", "fake", "anything", 3) == ""


# ---- 3. profile is append-only ---------------------------------------------

def test_profile_bootstraps_and_appends_without_touching_preferences(tmp_path):
    text = vault.read_profile(str(tmp_path), "Profile.md")
    assert "## Standing Preferences" in text

    path = tmp_path / "Profile.md"
    edited = path.read_text(encoding="utf-8").replace(
        "## Session Log", "Always be terse.\n\n## Session Log"
    )
    path.write_text(edited, encoding="utf-8")
    prefs_before = edited.split("## Session Log")[0]

    vault.append_profile_session(str(tmp_path), "Profile.md", "2026-09-28", "MCP", "- likes protocols")
    vault.append_profile_session(str(tmp_path), "Profile.md", "2026-09-29", "RAG", "- likes retrieval")

    after = path.read_text(encoding="utf-8")
    assert after.split("## Session Log")[0] == prefs_before  # human section byte-identical
    assert "### 2026-09-28 — MCP" in after and "### 2026-09-29 — RAG" in after
    # older entry is preserved, not overwritten
    assert "likes protocols" in after and "likes retrieval" in after


# ---- 6. internal-doc retriever ----------------------------------------------

def test_local_docs_search_ranks_and_cites(tmp_path):
    from research_assistant.documents import local_docs_search

    (tmp_path / "db.md").write_text("Postgres is our primary database. Redis is the cache.")
    (tmp_path / "food.txt").write_text("Cooking pasta takes ten minutes.")
    (tmp_path / "ignored.png").write_bytes(b"\x89PNG")

    out = local_docs_search(
        "which postgres database?", str(tmp_path), "unused", top_k=1,
        embeddings=KeywordEmbeddings(),
    )
    assert len(out["results"]) == 1
    hit = out["results"][0]
    assert hit["title"] == "db.md (page 1)"
    assert hit["url"] == "doc://db.md/p1-c1"
    assert "Postgres" in hit["raw_content"]


def test_local_docs_search_reads_pdf_pages(tmp_path):
    from pypdf import PdfWriter

    from research_assistant.documents import load_documents

    w = PdfWriter()
    w.add_blank_page(200, 200)
    with open(tmp_path / "blank.pdf", "wb") as f:
        w.write(f)
    # blank page has no text -> skipped, but must not crash
    assert load_documents(str(tmp_path)) == []


def test_local_docs_search_missing_folder_is_empty(tmp_path):
    from research_assistant.documents import local_docs_search

    assert local_docs_search("q", str(tmp_path / "nope"), "m") == {"results": []}
    assert local_docs_search("q", "", "m") == {"results": []}


def test_local_docs_results_archive_cleanly(tmp_path):
    from research_assistant.documents import local_docs_search

    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "handbook.pdf.md").write_text("Redis retrieval context")
    res = local_docs_search("redis", str(docs), "m", embeddings=KeywordEmbeddings())
    archived = vault.archive_sources(
        str(tmp_path / "vault"), "Sources", "topic", "2026-01-01", "redis", "local_docs", res
    )
    text = open(archived[0]["file_path"], encoding="utf-8").read()
    assert "Redis retrieval context" in text and "Binary" not in text


def test_write_report_cites_each_url_once(tmp_path):
    res = {"results": [{"url": "doc://a.md/p1-c1", "title": "A", "content": "x", "raw_content": "x"}]}
    archived = vault.archive_sources(str(tmp_path), "Sources", "t", "2026-01-01", "q1", "local_docs", res)
    archived += vault.archive_sources(str(tmp_path), "Sources", "t", "2026-01-01", "q2", "local_docs", res)
    path = vault.write_report(
        str(tmp_path), "Research", "Sources", "2026-01-01", "t", "T", "body", archived, loops=2
    )
    post = frontmatter.load(path)
    assert post["sources_count"] == 1
    assert post.content.count("doc://a.md/p1-c1") == 1
