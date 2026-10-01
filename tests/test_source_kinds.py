"""PDFs and web pages are told apart (and linked) from ingest to the finished report."""

from langchain_core.embeddings import Embeddings

from research_assistant import deep_report as d
from research_assistant import knowledge as k


class Emb(Embeddings):
    def _e(self, t):
        t = t.lower()
        v = [float(t.count(w)) for w in ("hybrid", "tokenizer", "chunk")]
        return v if any(v) else [0.001] * 3

    def embed_documents(self, texts):
        return [self._e(t) for t in texts]

    def embed_query(self, text):
        return self._e(text)


FRONT = ("---\nsource: web\nurl: https://example.org/guide\nquestion: Which tokenizer is best for Telugu?\n"
         "title: A Tokenizer Guide\n---\n# A Tokenizer Guide\n\nThe hybrid tokenizer reached 0.78 recall in this test.\n")


# ---- classification ----------------------------------------------------------------------------------

def test_classify_source():
    assert k.classify_source("Library/a.pdf", {}) == ("pdf", "")
    assert k.classify_source("Library/x/p.md", {"source": "arxiv", "source_id": "2603.25333v1"}) == (
        "pdf", "https://arxiv.org/abs/2603.25333v1")
    assert k.classify_source("Library/x/p.md", {"source": "arxiv", "url": "https://arxiv.org/abs/1"})[1] == "https://arxiv.org/abs/1"
    assert k.classify_source("Library/x/p.md", {"source": "europepmc", "url": "https://europepmc.org/a"}) == (
        "paper", "https://europepmc.org/a")
    assert k.classify_source("Library/x/p.md", {"source": "web", "url": "https://a.example/p"}) == ("web", "https://a.example/p")
    assert k.classify_source("Library/x/p.md", {"source": "seed", "url": "https://a.example/file.pdf"})[0] == "pdf"
    assert k.classify_source("Sources/a/p.md", {"url": "doc://runbook.md/p1"}) == ("document", "")   # not a web address
    assert k.classify_source("notes/a.md", {}) == ("document", "")


def test_front_matter_is_split_off():
    front, body = k.split_front_matter(FRONT)
    assert front["url"] == "https://example.org/guide" and body.startswith("# A Tokenizer Guide")
    assert k.split_front_matter("# no front matter\n\ntext") == ({}, "# no front matter\n\ntext")
    assert k.split_front_matter("---\nnot: [valid\n---\nbody")[0] == {}                 # broken YAML: left alone


# ---- ingest and search -------------------------------------------------------------------------------

def test_ingest_records_kind_url_and_keeps_provenance_text_out_of_the_index(tmp_path):
    kb = k.KnowledgeBase(tmp_path / "kb.sqlite", Emb())
    kb.ingest_text("Library/g/guide.md", FRONT)
    kb.ingest_text("Library/paper.pdf", "# A Paper\n\nHybrid chunking helps recall a lot in our experiments here.\n")
    rows = dict(kb.db.execute("SELECT path, source_kind FROM docs").fetchall())
    assert rows == {"Library/g/guide.md": "web", "Library/paper.pdf": "pdf"}
    title, url = kb.db.execute("SELECT title, source_url FROM docs WHERE path='Library/g/guide.md'").fetchone()
    assert (title, url) == ("A Tokenizer Guide", "https://example.org/guide")
    # the question the page was found for lives in the front matter: it must not become searchable text
    chunk_text = " ".join(r[0] for r in kb.db.execute("SELECT text FROM chunks WHERE doc_id=1").fetchall())
    assert "Which tokenizer is best for Telugu" not in chunk_text and "hybrid tokenizer reached" in chunk_text
    hit = next(h for h in kb.search("hybrid tokenizer recall", k=5) if h["path"] == "Library/g/guide.md")
    assert hit["source_kind"] == "web" and hit["source_url"] == "https://example.org/guide"


def test_rebuild_fills_in_kind_and_url_for_documents_stored_earlier(tmp_path):
    kb = k.KnowledgeBase(tmp_path / "kb.sqlite", Emb())
    kb.ingest_text("Library/g/guide.md", FRONT)
    kb.db.execute("UPDATE docs SET source_kind='', source_url=''")            # as the library was before this change
    kb.db.commit()
    kb.rebuild()
    assert kb.db.execute("SELECT source_kind, source_url FROM docs").fetchone() == ("web", "https://example.org/guide")


# ---- the report --------------------------------------------------------------------------------------

def _ev(i, source, url, kind):
    return d.Evidence(id=f"E{i}", claim=f"claim {i}", quote="q" * 20, source=source, heading="", sub_questions=[0],
                      url=url, kind=kind)


def test_sources_are_listed_as_papers_and_pdfs_and_web_pages_with_links():
    ev = [_ev(1, "Paper A", "https://arxiv.org/abs/1", "pdf"), _ev(2, "Paper A", "https://arxiv.org/abs/1", "pdf"),
          _ev(3, "Web B", "https://b.example/x", "web"), _ev(4, "Local note", "", "document"),
          _ev(5, "Old doc", "", "")]
    groups = dict(d.group_sources(ev, cited_ids={1, 3}))
    assert list(groups) == ["Papers and PDFs", "Web pages", "Other documents"]
    assert groups["Papers and PDFs"][0] == {"title": "Paper A", "url": "https://arxiv.org/abs/1", "kind": "pdf",
                                            "facts": 2, "cited": 1}
    assert [x["title"] for x in groups["Other documents"]] == ["Local note", "Old doc"]       # untyped goes to "other"
    plan = d.Plan(goal="g", title="T", sub_questions=["q"], outline=[{"title": "S", "questions": [0]}])
    report = d.assemble(plan, [("S", "Text [E1] and [E3].")], ev, lambda *a, **k: "Summary [E1].")
    assert "### Papers and PDFs (1)" in report and "- [Paper A](https://arxiv.org/abs/1) - 2 fact(s), 1 cited" in report
    assert "### Web pages (1)" in report and "- [Web B](https://b.example/x)" in report
    assert "- Local note - 1 fact(s), 0 cited" in report
    assert "1 papers and pdfs; 1 web pages; 2 other documents" in report


def test_the_report_header_does_not_paste_a_whole_prompt():
    long_goal = "MY GOAL\nI want to build a small model.\n\nCORE QUESTION\n" + "details " * 200
    line = d.goal_line(long_goal)
    assert line.startswith("I want to build a small model.") and len(line) < 420 and line.endswith("...")
    assert d.goal_line("Short goal") == "Short goal"
