"""The source fetcher, tested offline: canned API responses, a fake clock, a fake model."""

import json

import frontmatter
import httpx

from research_assistant import fetcher as f

ARXIV_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2005.11401v4</id>
    <title>Retrieval-Augmented
      Generation for Knowledge-Intensive NLP Tasks</title>
    <summary>We explore a general-purpose fine-tuning recipe for retrieval-augmented generation.</summary>
    <published>2020-05-22T00:00:00Z</published>
    <author><name>Patrick Lewis</name></author><author><name>Ethan Perez</name></author>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/9999.00001v1</id>
    <title>A Paper About Cooking Pasta</title>
    <summary>Boil water, add salt.</summary>
    <published>2021-01-01T00:00:00Z</published>
    <author><name>A. Cook</name></author>
  </entry>
</feed>"""

EPMC_JSON = {"resultList": {"result": [
    {"id": "123", "source": "MED", "pmcid": "PMC111", "isOpenAccess": "Y", "title": "Hybrid <i>retrieval</i> in clinics",
     "abstractText": "We study <b>retrieval</b>.", "authorString": "Doe J.", "firstPublicationDate": "2023-04-01",
     "license": "cc by"},
    {"id": "456", "source": "MED", "pmcid": "PMC222", "isOpenAccess": "N", "title": "Closed paper"},
    {"id": "789", "source": "MED", "isOpenAccess": "Y", "title": "No PMC id"}]}}

JATS = """<article><front><article-meta><title-group><article-title>Hybrid retrieval in clinics</article-title>
</title-group><abstract><p>We study retrieval.</p></abstract></article-meta></front>
<body><sec><title>Methods</title><p>We indexed 500 guidelines.</p>
<table-wrap><caption><p>Table 1 Recall</p></caption><table><tr><th>Method</th><th>Recall</th></tr>
<tr><td>BM25</td><td>0.61</td></tr><tr><td>Hybrid</td><td>0.78</td></tr></table></table-wrap></sec></body></article>"""

LONG_HTML = "<html><head><title>Hybrid search guide</title></head><body><article><h1>Hybrid search guide</h1>" + \
    "".join(f"<p>Paragraph {i}: hybrid retrieval combines keyword and vector search to improve recall on real corpora.</p>"
            for i in range(30)) + "</article></body></html>"


class Clock:
    """Fake clock: sleeping advances time, so throttling is testable without waiting."""

    def __init__(self):
        self.t = 1000.0
        self.slept: list[float] = []

    def now(self):
        return self.t

    def sleep(self, s):
        self.slept.append(s)
        self.t += s


PUBLIC_IP = "93.184.216.34"
INTERNAL = {"localhost": "127.0.0.1", "intranet.example": "10.0.0.5", "metadata.example": "169.254.169.254",
            "carrier.example": "100.64.0.1", "v6loop.example": "::1", "mapped.example": "::ffff:127.0.0.1"}


def fake_resolve(host):
    """Tests never touch DNS: known internal names map to internal addresses, everything else is 'public'."""
    return [host if host[0].isdigit() else INTERNAL.get(host, PUBLIC_IP)]


def make_fetcher(handler, clock=None):
    clock = clock or Clock()
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return f.Fetcher(http=http, contact="me@example.com", sleep=clock.sleep, now=clock.now,
                     resolve=fake_resolve), clock


# ---- politeness ---------------------------------------------------------------

def test_arxiv_requests_are_spaced_at_least_three_seconds_apart():
    fetcher, clock = make_fetcher(lambda r: httpx.Response(200, text=ARXIV_XML))
    fetcher.search_arxiv("retrieval")
    fetcher.search_arxiv("graphs")
    fetcher.search_arxiv("self correction")
    assert len(clock.slept) == 2 and all(s >= 2.99 for s in clock.slept)


def test_other_hosts_get_a_default_gap_and_hosts_are_independent():
    fetcher, clock = make_fetcher(lambda r: httpx.Response(200, text="x"))
    fetcher.get("https://a.example/1")
    fetcher.get("https://b.example/1")                     # different host: no wait
    assert clock.slept == []
    fetcher.get("https://a.example/2")
    assert clock.slept and abs(clock.slept[0] - f.DEFAULT_INTERVAL) < 0.01


def test_requests_identify_the_tool_and_a_contact():
    seen = {}

    def handler(request):
        seen["ua"] = request.headers["user-agent"]
        return httpx.Response(200, text=ARXIV_XML)

    fetcher, _ = make_fetcher(handler)
    fetcher.search_arxiv("x")
    assert "ResearchAssistant" in seen["ua"] and "me@example.com" in seen["ua"]


def test_robots_txt_crawl_delay_is_honored():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nCrawl-delay: 10\nAllow: /")
        return httpx.Response(200, text=LONG_HTML, headers={"content-type": "text/html"})

    fetcher, clock = make_fetcher(handler)
    assert fetcher.allowed("https://slow.example/a")
    fetcher.get("https://slow.example/a")
    fetcher.get("https://slow.example/b")
    assert max(clock.slept) >= 9.99


# ---- robots / paywalls / thin pages ------------------------------------------------------

def test_seed_blocked_by_robots_is_skipped_with_a_reason():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text="User-agent: *\nDisallow: /private")
        return httpx.Response(200, text=LONG_HTML)

    fetcher, _ = make_fetcher(handler)
    cand, reason, _ = fetcher.fetch_seed("https://site.example/private/page")
    assert cand is None and "robots.txt" in reason
    ok, _, _ = fetcher.fetch_seed("https://site.example/public/page")
    assert ok is not None and ok.title == "Hybrid search guide" and "hybrid retrieval" in ok.full_text


def test_missing_robots_allows_but_a_broken_robots_server_blocks():
    def handler_404(request):
        return httpx.Response(404) if request.url.path == "/robots.txt" else httpx.Response(200, text=LONG_HTML)

    def handler_500(request):
        return httpx.Response(500) if request.url.path == "/robots.txt" else httpx.Response(200, text=LONG_HTML)

    assert make_fetcher(handler_404)[0].allowed("https://x.example/a") is True
    assert make_fetcher(handler_500)[0].allowed("https://y.example/a") is False


def test_paywall_login_and_thin_pages_are_skipped_not_saved():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if "paywall" in request.url.path:
            return httpx.Response(403)
        return httpx.Response(200, text="<html><body><p>Please log in.</p></body></html>")

    fetcher, _ = make_fetcher(handler)
    assert "login or paywall" in fetcher.fetch_seed("https://news.example/paywall/a")[1]
    assert "too little text" in fetcher.fetch_seed("https://news.example/thin")[1]


# ---- parsing --------------------------------------------------------------------

def test_parse_arxiv_entries():
    cands = f.parse_arxiv(ARXIV_XML)
    assert [c.id for c in cands] == ["2005.11401v4", "9999.00001v1"]
    assert cands[0].title == "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"   # whitespace collapsed
    assert cands[0].url == "https://arxiv.org/pdf/2005.11401v4" and cands[0].authors == "Patrick Lewis, Ethan Perez"
    assert cands[0].published == "2020-05-22"


def test_parse_europepmc_keeps_only_open_access_with_a_pmcid():
    cands = f.parse_europepmc(EPMC_JSON)
    assert [c.id for c in cands] == ["PMC111"]
    assert cands[0].title == "Hybrid retrieval in clinics" and cands[0].summary == "We study retrieval."
    assert "cc by" in cands[0].licence


def test_jats_full_text_becomes_markdown_with_a_real_table():
    md = f.jats_to_markdown(JATS)
    assert md.startswith("# Hybrid retrieval in clinics") and "## Abstract" in md and "## Methods" in md
    assert "| Method | Recall |" in md and "| Hybrid | 0.78 |" in md


# ---- the whole job --------------------------------------------------------------

def fake_llm(prompt, json_mode=False):
    if "keyword search query" in prompt:
        return json.dumps({"query": "hybrid retrieval"})
    if "How useful is this source" in prompt:
        return json.dumps({"score": 0 if "Cooking" in prompt else 3})
    return "{}"


def collect_handler(request):
    url = str(request.url)
    if "export.arxiv.org" in url:
        return httpx.Response(200, text=ARXIV_XML)
    if "europepmc/webservices/rest/search" in url:
        return httpx.Response(200, json=EPMC_JSON)
    if url.endswith("fullTextXML"):
        return httpx.Response(200, text=JATS * 1)
    if "arxiv.org/pdf/" in url:
        return httpx.Response(200, content=b"%PDF-fake")
    return httpx.Response(404)


def fake_pdf_to_md(pdf_bytes, name):
    return f"# Converted {name}\n\n" + "Hybrid retrieval improves recall on real corpora. " * 40


def test_collect_triages_saves_with_provenance_and_writes_a_manifest(tmp_path):
    fetcher, _ = make_fetcher(collect_handler)
    store = f.SourceStore(tmp_path / "Library", "hybrid-retrieval")
    big_jats = JATS.replace("We indexed 500 guidelines.", "We indexed 500 guidelines. " * 60)
    fetcher.europepmc_fulltext = lambda pmcid: f.jats_to_markdown(big_jats)
    summary = f.collect(["Does hybrid retrieval help?"], store, fetcher, fake_llm, convert_pdf=fake_pdf_to_md)

    assert summary["saved"] == 2 and summary["skipped"] >= 1          # paper + clinical OA article; cooking skipped
    manifest = json.loads((tmp_path / "Library" / "hybrid-retrieval" / "manifest.json").read_text(encoding="utf-8"))
    by_title = {m["title"]: m for m in manifest}
    assert by_title["A Paper About Cooking Pasta"]["status"] == "skipped"
    assert "relevance 0" in by_title["A Paper About Cooking Pasta"]["reason"]
    saved = [m for m in manifest if m["status"] == "saved"]
    post = frontmatter.load(saved[0]["file"])
    assert post["source"] in ("arxiv", "europepmc") and post["fetched_at"] and post["licence"] and post["relevance"] == 3
    assert post["question"] == "Does hybrid retrieval help?" and len(post.content) > f.MIN_TEXT_CHARS
    assert list((tmp_path / "Library" / "hybrid-retrieval" / "raw").glob("*.pdf"))   # original kept for re-parsing


def test_the_same_paper_is_never_saved_twice_across_runs(tmp_path):
    lib = tmp_path / "Library"
    fetcher, _ = make_fetcher(collect_handler)
    fetcher.europepmc_fulltext = lambda pmcid: f.jats_to_markdown(JATS.replace("We indexed 500 guidelines.", "x " * 500))
    first = f.collect(["q1"], f.SourceStore(lib, "run-one"), fetcher, fake_llm, convert_pdf=fake_pdf_to_md)
    second = f.collect(["q1"], f.SourceStore(lib, "run-two"), fetcher, fake_llm, convert_pdf=fake_pdf_to_md)
    assert first["saved"] == 2 and second["saved"] == 0
    manifest = json.loads((lib / "run-two" / "manifest.json").read_text(encoding="utf-8"))
    assert any("already in the library" in m["reason"] for m in manifest)


def test_identical_content_under_a_different_id_is_caught_by_hash(tmp_path):
    store = f.SourceStore(tmp_path / "Library", "x")
    a = f.Candidate(source="arxiv", id="1111.1", title="Paper", page_url="http://arxiv.org/abs/1111.1")
    b = f.Candidate(source="seed", id="mirror", title="Paper (mirror)", page_url="http://mirror.example/p")
    text = "same body " * 200
    assert store.save(a, text) is not None
    assert store.save(b, text) is None and store.manifest[-1]["reason"].startswith("duplicate")


def test_the_cap_and_failures_are_respected(tmp_path):
    def handler(request):
        url = str(request.url)
        if "arxiv.org/pdf/" in url:
            return httpx.Response(500)                           # every PDF download fails
        return collect_handler(request)

    fetcher, _ = make_fetcher(handler)
    store = f.SourceStore(tmp_path / "Library", "fail")
    summary = f.collect(["q"], store, fetcher, fake_llm, convert_pdf=fake_pdf_to_md, max_sources=1)
    assert summary["failed"] >= 1                                # recorded, not raised
    capped = f.collect(["q"], f.SourceStore(tmp_path / "Library", "cap"), make_fetcher(collect_handler)[0], fake_llm,
                       convert_pdf=fake_pdf_to_md, max_sources=1)
    assert capped["saved"] == 1


def test_seed_urls_are_fetched_politely_and_saved(tmp_path):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, text=LONG_HTML, headers={"content-type": "text/html"})

    fetcher, _ = make_fetcher(handler)
    store = f.SourceStore(tmp_path / "Library", "seeds")
    summary = f.collect([], store, fetcher, fake_llm, seeds=["https://blog.example/hybrid-guide"])
    assert summary["saved"] == 1
    post = frontmatter.load(next((tmp_path / "Library" / "seeds").glob("*.md")))
    assert post["source"] == "seed" and "private use" in post["licence"]


def test_search_terms_fall_back_to_keywords_when_the_model_fails():
    assert f.search_terms("What are the failure modes of retrieval systems with long context?", lambda p, json_mode=False: "") \
        == "failure modes retrieval systems long context"


def test_arxiv_query_ands_every_keyword_with_the_all_field():
    assert f.arxiv_query("hybrid retrieval augmented generation") == \
        "all:hybrid AND all:retrieval AND all:augmented AND all:generation"
    assert f.arxiv_query("a b c d e f g").count("AND") == 4                # capped at 5 terms
    seen = {}

    def handler(request):
        seen["q"] = str(request.url)
        return httpx.Response(200, text=ARXIV_XML)

    make_fetcher(handler)[0].search_arxiv("hybrid retrieval")
    assert "all%3Ahybrid%20AND%20all%3Aretrieval" in seen["q"]


def test_a_small_cap_is_shared_between_sources_not_filled_by_the_first(tmp_path):
    fetcher, _ = make_fetcher(collect_handler)
    fetcher.europepmc_fulltext = lambda pmcid: f.jats_to_markdown(JATS.replace("We indexed 500 guidelines.", "x " * 500))
    store = f.SourceStore(tmp_path / "Library", "share")
    f.collect(["q"], store, fetcher, fake_llm, convert_pdf=fake_pdf_to_md, max_sources=2)
    sources = [m["source"] for m in store.manifest if m["status"] == "saved"]
    assert sorted(sources) == ["arxiv", "europepmc"]          # one of each, not two arXiv papers


def test_a_timeout_gets_one_retry_then_fails_cleanly():
    calls = []

    def flaky(request):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(200, text="ok")

    fetcher, _ = make_fetcher(flaky)
    assert fetcher.get("https://slow.example/x").text == "ok" and len(calls) == 2

    def dead(request):
        raise httpx.ReadTimeout("dead", request=request)

    fetcher2, _ = make_fetcher(dead)
    try:
        fetcher2.get("https://dead.example/x")
        raise AssertionError("should have raised")
    except httpx.TimeoutException:
        pass


def test_deleting_a_saved_file_lets_it_be_fetched_again(tmp_path):
    store = f.SourceStore(tmp_path / "Library", "x")
    c = f.Candidate(source="arxiv", id="1234.5", title="Paper", page_url="http://arxiv.org/abs/1234.5")
    path = store.save(c, "body text " * 200)
    assert store.seen(c) == path
    import os

    os.remove(path)
    assert store.seen(c) is None                               # stale entry forgotten
    assert store.save(c, "body text " * 200) is not None       # and it can be saved again


def test_the_default_relevance_bar_is_high_enough_to_keep_tangential_papers_out(tmp_path):
    def two_scores(prompt, json_mode=False):
        if "keyword search query" in prompt:
            return json.dumps({"query": "hybrid retrieval"})
        return json.dumps({"score": 2 if "Cooking" in prompt else 3})     # the off-topic paper scores a loose 2

    fetcher, _ = make_fetcher(collect_handler)
    fetcher.europepmc_fulltext = lambda pmcid: f.jats_to_markdown(JATS.replace("We indexed 500 guidelines.", "x " * 500))
    store = f.SourceStore(tmp_path / "Library", "bar")
    f.collect(["q"], store, fetcher, two_scores, convert_pdf=fake_pdf_to_md)
    cooking = next(m for m in store.manifest if "Cooking" in m["title"])
    assert cooking["status"] == "skipped" and "relevance 2 < 3" in cooking["reason"]


# ---- SSRF guard, size cap, redirects, id validation --------------------------------------

import pytest  # noqa: E402


@pytest.mark.parametrize("url", [
    "http://localhost/admin", "http://127.0.0.1:2025/threads", "http://intranet.example/x", "http://10.1.2.3/x",
    "http://metadata.example/latest/meta-data", "http://169.254.169.254/latest/meta-data",
    "http://carrier.example/x", "http://v6loop.example/x", "http://mapped.example/x",
    "file:///C:/Windows/win.ini", "ftp://example.org/x", "http://user:pw@example.org/x", "javascript:alert(1)"])
def test_internal_and_non_http_seed_urls_are_refused_without_any_request(url):
    calls = []
    fetcher, _ = make_fetcher(lambda r: calls.append(str(r.url)) or httpx.Response(200, text="secret"))
    cand, reason, raw = fetcher.fetch_seed(url)
    assert cand is None and raw is None and reason.startswith("blocked") and calls == []


def test_a_public_url_that_redirects_to_an_internal_address_is_blocked():
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.host == "public.example":
            return httpx.Response(302, headers={"location": "http://metadata.example/latest/meta-data"})
        return httpx.Response(200, text="INTERNAL SECRET " * 100)

    fetcher, _ = make_fetcher(handler)
    cand, reason, _ = fetcher.fetch_seed("https://public.example/go")
    assert cand is None and "non-public" in reason
    assert not any("metadata.example" in c for c in calls)        # the internal host was never contacted


def test_public_redirects_are_followed_but_not_forever():
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/a":
            return httpx.Response(301, headers={"location": "/b"})
        if request.url.path == "/b":
            return httpx.Response(200, text="<html><body>" + "<p>hybrid retrieval recall text</p>" * 60 + "</body></html>",
                                  headers={"content-type": "text/html"})
        return httpx.Response(302, headers={"location": request.url.path + "x"})       # endless chain

    fetcher, _ = make_fetcher(handler)
    assert fetcher.fetch_seed("https://site.example/a")[0] is not None
    cand, reason, _ = fetcher.fetch_seed("https://loop.example/r")
    assert cand is None and "redirects" in reason


def test_oversize_responses_are_cut_off_not_read_into_memory(monkeypatch):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, content=b"x" * 50_000, headers={"content-type": "application/pdf"})

    fetcher, _ = make_fetcher(handler)
    with pytest.raises(f.TooLarge):
        fetcher.get_public("https://big.example/file.pdf", max_bytes=10_000)
    monkeypatch.setattr(f, "MAX_BYTES", 10_000)
    cand, reason, raw = fetcher.fetch_seed("https://big.example/file.pdf")
    assert cand is None and raw is None and "larger" in reason


def test_the_arxiv_api_and_pdf_hosts_share_one_rate_limit():
    fetcher, clock = make_fetcher(lambda r: httpx.Response(200, text=ARXIV_XML))
    fetcher.get("http://export.arxiv.org/api/query?search_query=x")
    fetcher.get("https://arxiv.org/pdf/2005.11401")
    assert clock.slept and clock.slept[0] >= 2.99


def test_malformed_ids_never_reach_a_url():
    bad = ARXIV_XML.replace("2005.11401v4", "x@evil.example/../../etc")
    assert f.parse_arxiv(bad)[0].id == "9999.00001v1"                        # the malformed entry is dropped
    assert f.parse_europepmc({"resultList": {"result": [
        {"pmcid": "PMC1/../../x", "isOpenAccess": "Y", "title": "t"}]}}) == []
    fetcher, _ = make_fetcher(lambda r: httpx.Response(200, text="x"))
    with pytest.raises(ValueError):
        fetcher.europepmc_fulltext("PMC1/../../x")


def test_null_titles_and_arxiv_error_feeds_do_not_break_a_search():
    cands = f.parse_europepmc({"resultList": {"result": [
        {"pmcid": "PMC9", "isOpenAccess": "Y", "title": None, "abstractText": None, "authorString": None}]}})
    assert cands[0].title == "PMC9" and cands[0].summary == ""
    error_feed = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/api/errors#incorrect_id</id>
    <title>Error</title><summary>bad</summary></entry></feed>"""
    assert f.parse_arxiv(error_feed) == []
