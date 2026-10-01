"""The web collector, offline: a fake search engine, canned pages, a fake clock and a fake model."""

import json

import frontmatter
import httpx
from tests_helpers import fake_pdf_to_md, make_fetcher

from research_assistant import collector as c
from research_assistant import fetcher as f


def page(title: str) -> str:
    body = "".join(f"<p>Paragraph {i}: hybrid retrieval combines keyword and vector search to improve recall "
                   "on real corpora.</p>" for i in range(30))
    return f"<html><head><title>{title}</title></head><body><article><h1>{title}</h1>{body}</article></body></html>"


ARXIV = """<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><entry>
<id>http://arxiv.org/abs/2005.11401v4</id><title>RAG for knowledge tasks</title>
<summary>retrieval augmented generation</summary><published>2020-05-22T00:00:00Z</published>
<author><name>P. Lewis</name></author></entry></feed>"""


def llm_by_title(good: str):
    """Triage returns 3 for candidates whose text contains `good`, 1 for 'maybe', else 0."""
    def llm(prompt, json_mode=False):
        if "keyword search query" in prompt:
            return json.dumps({"query": "hybrid retrieval"})
        if "How useful is this source" in prompt:
            candidate = prompt.split("Candidate source:")[1]          # judge the source, not the question
            return json.dumps({"score": 3 if good in candidate else 1 if "maybe" in candidate else 0})
        return "{}"
    return llm


def routes(request):
    url = str(request.url)
    if "export.arxiv.org" in url:
        return httpx.Response(200, text=ARXIV)
    if "europepmc" in url:
        return httpx.Response(200, json={"resultList": {"result": []}})
    if url.endswith("robots.txt"):
        return httpx.Response(404)
    host = request.url.host
    return httpx.Response(200, text=page(f"Page from {host}"), headers={"content-type": "text/html"})


def search_of(hits):
    return lambda query, n: [c.Hit(*h) for h in hits]


def store_in(tmp_path):
    return f.SourceStore(tmp_path / "Library", "2026-10-01-goal")


# ---- domain rules ------------------------------------------------------------------------

def test_domain_rules():
    assert c.domain_ok("https://www.who.int/x", ["who.int"], [])
    assert not c.domain_ok("https://evil-who.int.example.com/x", ["who.int"], [])
    assert c.domain_ok("https://health.gov.in/a", ["*.gov.in"], [])
    assert not c.domain_ok("https://blog.example.com", ["who.int", "cdc.gov"], [])
    assert c.domain_ok("https://blog.example.com", [], [])
    assert not c.domain_ok("https://ads.example.com/x", [], ["example.com"])      # block-list wins
    assert not c.domain_ok("not a url", [], [])
    assert c.split_domains("who.int; cdc.gov, nhs.uk") == ["who.int", "cdc.gov", "nhs.uk"]


# ---- discover ----------------------------------------------------------------------------

def test_discover_returns_judged_candidates_and_drops_duplicates_and_irrelevant(tmp_path):
    fx, _ = make_fetcher(routes)
    hits = [("Good guide hybrid", "https://a.example/guide?utm_source=x", "all about hybrid"),
            ("Good guide hybrid", "https://a.example/guide", "same page, tracking removed"),
            ("Unrelated cooking", "https://b.example/pasta", "boil water"),
            ("maybe useful", "https://c.example/maybe", "maybe")]
    out = c.discover(["Does hybrid help?"], search=search_of(hits), fx=fx, store=store_in(tmp_path),
                     llm=llm_by_title("hybrid"), include_papers=False)
    titles = [d["title"] for d in out]
    assert titles.count("Good guide hybrid") == 1                  # the same URL (minus tracking) shown once
    assert "Unrelated cooking" not in titles                        # score 0 is below min_score
    assert out[0]["score"] == 3 and out[-1]["score"] == 1           # best first
    first = out[0]
    assert first["kind"] == "page" and first["site"] == "a.example" and first["question_index"] == 0
    assert first["id"].startswith("web:")


def test_discover_mixes_in_papers_and_marks_them(tmp_path):
    fx, _ = make_fetcher(routes)
    out = c.discover(["Does hybrid help?"], search=search_of([("Good hybrid page", "https://a.example/x", "hybrid")]),
                     fx=fx, store=store_in(tmp_path), llm=lambda p, json_mode=False: json.dumps({"score": 3, "query": "q"}))
    kinds = {d["kind"] for d in out}
    assert kinds == {"page", "paper"}
    assert any(d["source"] == "arxiv" and d["pdf_url"] for d in out)


def test_allow_list_filters_web_results(tmp_path):
    fx, _ = make_fetcher(routes)
    hits = [("Official hybrid", "https://www.who.int/x", "hybrid"), ("Blog hybrid", "https://blog.example/x", "hybrid")]
    out = c.discover(["q"], search=search_of(hits), fx=fx, store=store_in(tmp_path), llm=llm_by_title("hybrid"),
                     include_papers=False, allow=["who.int"])
    assert [d["site"] for d in out] == ["www.who.int"]


def test_search_failure_is_reported_not_fatal(tmp_path):
    fx, _ = make_fetcher(routes)
    messages = []

    def broken(query, n):
        raise RuntimeError("rate limited")

    out = c.discover(["q"], search=broken, fx=fx, store=store_in(tmp_path),
                     llm=lambda p, json_mode=False: json.dumps({"score": 3, "query": "q"}), on_progress=messages.append)
    assert any("web search failed" in m for m in messages)
    assert any(d["kind"] == "paper" for d in out)                   # the paper search still worked


def test_candidate_cap_and_source_already_saved(tmp_path):
    fx, _ = make_fetcher(routes)
    store = store_in(tmp_path)
    seen = c._web_candidate(c.Hit("Saved before hybrid", "https://a.example/saved", "hybrid"), "q")
    store.save(seen, "x" * 900)
    hits = [(f"Hybrid page {i}", f"https://a.example/p{i}", "hybrid") for i in range(10)]
    hits.append(("Saved before hybrid", "https://a.example/saved", "hybrid"))
    out = c.discover(["q"], search=search_of(hits), fx=fx, store=store, llm=llm_by_title("ybrid"),
                     include_papers=False, max_candidates=4, per_question=20)
    assert len(out) == 4 and all("Saved before" not in d["title"] for d in out)


def test_discovery_is_sequential_with_a_pause_between_questions(tmp_path):
    fx, clock = make_fetcher(routes)
    order = []

    def search(query, n):
        order.append(query)
        return []

    c.discover(["q1", "q2", "q3"], search=search, fx=fx, store=store_in(tmp_path), llm=llm_by_title("x"),
               include_papers=False, search_pause=2.0)
    assert len(order) == 3 and clock.slept.count(2.0) == 3


# ---- collect -----------------------------------------------------------------------------

def test_collect_saves_pages_as_markdown_with_provenance_and_a_manifest(tmp_path):
    fx, _ = make_fetcher(routes)
    store = store_in(tmp_path)
    cands = [c.from_dict(d) for d in c.discover(
        ["Does hybrid help?"], search=search_of([("Hybrid guide", "https://a.example/guide", "hybrid")]), fx=fx,
        store=store, llm=lambda p, json_mode=False: json.dumps({"score": 3, "query": "q"}), include_papers=False)]
    summary = c.collect_selected(cands, store, fx, convert_pdf=fake_pdf_to_md)
    assert summary["saved"] == 1 and summary["pages"] == 1 and summary["papers"] == 0
    saved = next(store.dir.glob("*.md"))
    post = frontmatter.load(saved)
    assert post["url"] == "https://a.example/guide" and post["question"] == "Does hybrid help?"
    assert "hybrid retrieval combines" in post.content
    manifest = json.loads((store.dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest[0]["status"] == "saved"


def test_collect_refuses_internal_addresses_and_robots_and_keeps_going(tmp_path):
    def handler(request):
        if request.url.path == "/robots.txt" and request.url.host == "blocked.example":
            return httpx.Response(200, text="User-agent: *\nDisallow: /")
        return routes(request)

    fx, _ = make_fetcher(handler)
    fx.resolve = lambda host: ["10.0.0.5"] if host == "intranet.example" else ["93.184.216.34"]
    store = store_in(tmp_path)
    cands = [c._web_candidate(c.Hit("Internal", "http://intranet.example/secret", ""), "q"),
             c._web_candidate(c.Hit("Blocked", "https://blocked.example/page", ""), "q"),
             c._web_candidate(c.Hit("Fine", "https://fine.example/page", ""), "q")]
    summary = c.collect_selected(cands, store, fx, convert_pdf=fake_pdf_to_md)
    reasons = {m["title"]: (m["status"], m["reason"]) for m in store.manifest}
    assert reasons["Internal"][0] == "skipped" and "non-public" in reasons["Internal"][1]
    assert reasons["Blocked"][0] == "skipped" and "robots" in reasons["Blocked"][1]
    assert summary["saved"] == 1


def test_collect_is_one_at_a_time_and_respects_the_source_limit(tmp_path):
    inflight, peak, order = [0], [0], []

    def handler(request):
        if request.url.path != "/robots.txt":
            inflight[0] += 1
            peak[0] = max(peak[0], inflight[0])
            order.append(request.url.host)
            inflight[0] -= 1
        return routes(request)

    fx, _ = make_fetcher(handler)
    store = store_in(tmp_path)
    cands = [c._web_candidate(c.Hit(f"P{i}", f"https://s{i}.example/p", ""), "q") for i in range(5)]
    summary = c.collect_selected(cands, store, fx, convert_pdf=fake_pdf_to_md, max_sources=2)
    assert order[:2] == ["s0.example", "s1.example"] and peak[0] == 1
    assert summary["saved"] == 2
    assert [m["status"] for m in store.manifest].count("skipped") == 3


def test_a_page_with_almost_no_text_is_skipped(tmp_path):
    fx, _ = make_fetcher(lambda r: httpx.Response(404) if r.url.path == "/robots.txt"
                         else httpx.Response(200, text="<html><body><p>Please log in</p></body></html>"))
    store = store_in(tmp_path)
    summary = c.collect_selected([c._web_candidate(c.Hit("Login wall", "https://w.example/p", ""), "q")], store, fx)
    assert summary["saved"] == 0 and "too little text" in store.manifest[0]["reason"]


def test_candidate_dict_roundtrip():
    cand = c._web_candidate(c.Hit("T", "https://a.example/x", "snippet"), "q")
    cand.relevance = 2
    back = c.from_dict(c.to_dict(cand, 3))
    assert (back.source, back.id, back.url, back.question, back.relevance) == ("web", cand.id, cand.url, "q", 2)
