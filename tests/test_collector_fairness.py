"""Collector fixes from a real run: the source limit is shared fairly, and one paper is one source."""

import json

import httpx
from tests_helpers import make_fetcher

from research_assistant import collector as c
from research_assistant import fetcher as f

# ---- one paper, however it is addressed ----------------------------------------------------------------

def test_arxiv_key_matches_every_way_of_naming_the_same_paper():
    keys = {f.arxiv_key(u) for u in ("https://arxiv.org/abs/2603.25333", "https://arxiv.org/abs/2603.25333v1",
                                     "http://arxiv.org/pdf/2603.25333v2", "https://arxiv.org/pdf/2603.25333v1.pdf")}
    assert keys == {"arxiv:2603.25333"}
    assert f.arxiv_key("https://arxiv.org/abs/hep-th/9901001v2") == "arxiv:hep-th/9901001"
    assert f.arxiv_key("https://example.org/arxiv-style/2603.25333") is None
    assert f.arxiv_key("") is None


def test_the_store_treats_the_pdf_and_the_abs_page_as_the_same_source(tmp_path):
    store = f.SourceStore(tmp_path / "Library", "goal")
    pdf = f.Candidate(source="arxiv", id="2603.25333v1", title="Adaptive Chunking", url="http://arxiv.org/pdf/2603.25333v1")
    store.save(pdf, "text " * 300)
    page = c._web_candidate(c.Hit("Adaptive Chunking - arXiv.org", "https://arxiv.org/abs/2603.25333", ""), "q")
    assert store.seen(page) is not None                              # the web copy is recognised as already saved


# ---- discovery: no duplicates across kinds or questions ------------------------------------------------

ARXIV = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry>
<id>http://arxiv.org/abs/2603.25333v1</id><title>Adaptive Chunking</title><summary>chunking for RAG</summary>
<published>2026-03-26T00:00:00Z</published><author><name>A. B.</name></author></entry></feed>"""


def routes(request):
    url = str(request.url)
    if "export.arxiv.org" in url:
        return httpx.Response(200, text=ARXIV)
    if "europepmc" in url:
        return httpx.Response(200, json={"resultList": {"result": []}})
    return httpx.Response(404)


JUDGE = lambda prompt, json_mode=False: json.dumps({"score": 3, "query": "chunking"})  # noqa: E731


def test_a_paper_found_by_both_searches_is_listed_once_as_the_pdf(tmp_path):
    fx, _ = make_fetcher(routes)
    store = f.SourceStore(tmp_path / "Library", "goal")
    hits = [c.Hit("Adaptive Chunking - arXiv.org", "https://arxiv.org/abs/2603.25333v1", "chunking"),
            c.Hit("Another page", "https://blog.example/chunking", "chunking")]
    out = c.discover(["How should documents be chunked?"], search=lambda q, n: hits, fx=fx, store=store, llm=JUDGE)
    adaptive = [d for d in out if "Adaptive Chunking" in d["title"]]
    assert len(adaptive) == 1 and adaptive[0]["kind"] == "paper" and adaptive[0]["source"] == "arxiv"
    assert any(d["site"] == "blog.example" for d in out)


def test_the_same_paper_is_not_offered_again_for_a_later_question(tmp_path):
    fx, _ = make_fetcher(routes)
    store = f.SourceStore(tmp_path / "Library", "goal")
    out = c.discover(["Question one about chunking?", "Question two about chunking?"], search=lambda q, n: [], fx=fx,
                     store=store, llm=JUDGE)
    assert [d["question_index"] for d in out if "Adaptive Chunking" in d["title"]] == [0]


# ---- the limit is shared fairly ------------------------------------------------------------------------

def cand(q, score, name):
    return {"id": name, "question_index": q, "score": score}


def test_fair_order_takes_turns_across_questions_and_puts_the_best_first_within_each():
    items = [cand(0, 3, "q0-a"), cand(0, 3, "q0-b"), cand(0, 2, "q0-c"), cand(0, 3, "q0-d"),
             cand(1, 3, "q1-a"), cand(1, 2, "q1-b"), cand(2, 3, "q2-a")]
    order = [d["id"] for d in c.fair_order(items)]
    assert order == ["q0-a", "q1-a", "q2-a", "q0-b", "q1-b", "q0-d", "q0-c"]
    assert order[:3] == ["q0-a", "q1-a", "q2-a"]                     # a limit of 3 gives every question one source
    assert sorted(order) == sorted(d["id"] for d in items)


def test_the_best_match_beats_the_first_listed():
    order = [d["id"] for d in c.fair_order([cand(0, 2, "weak"), cand(0, 3, "strong")])]
    assert order == ["strong", "weak"]


def test_collecting_with_a_limit_reaches_later_questions(tmp_path, monkeypatch):
    from research_assistant import goal_graph
    monkeypatch.setenv("VAULT_PATH", str(tmp_path))
    monkeypatch.setenv("FETCH_MAX_SOURCES", "3")
    seen = {}

    def fake(todo, store, fx, **kw):
        seen["titles"] = [x.title for x in todo]
        seen["limit"] = kw["max_sources"]
        return {"saved": 0, "pages": 0, "papers": 0, "skipped": 0, "failed": 0, "folder": ""}

    monkeypatch.setattr(c, "collect_selected", fake)
    cands = []
    for q in range(3):
        for i in range(4):
            cand_ = c._web_candidate(c.Hit(f"Q{q} page {i}", f"https://s{q}{i}.example/p", ""), f"question {q}")
            cand_.relevance = 3
            cands.append(c.to_dict(cand_, q))
    state = {"goal": "g", "plan": {"title": "T", "sub_questions": ["a", "b", "c"]}, "candidates": cands,
             "selected_ids": [d["id"] for d in cands]}               # everything ticked, in question order
    goal_graph.collect(state, {"configurable": {"thread_id": "t"}})
    first_three = seen["titles"][: seen["limit"]]
    assert sorted(t.split()[0] for t in first_three) == ["Q0", "Q1", "Q2"]   # not all from question 0
