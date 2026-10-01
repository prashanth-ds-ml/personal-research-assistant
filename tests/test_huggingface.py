"""Hugging Face and AI-engineering-site collecting, and the removed limits. Fake responses shaped like the real API."""

import json

import frontmatter
import httpx
from tests_helpers import make_fetcher

from research_assistant import collector as c
from research_assistant import fetcher as f
from research_assistant.configuration import Configuration

PAPERS = [{"paper": {"id": "2512.15943", "title": "Small Language Models for\n Tool Calling", "summary": "We study  tool calling.",
                     "publishedAt": "2025-12-17T20:12:06.000Z", "authors": [{"name": "A. One"}, {"name": "B. Two"}, {"hidden": True}]}},
          {"paper": {"id": "not-an-arxiv-id", "title": "bad"}}, {"nope": 1}, "junk"]
MODELS = [{"id": "Qwen/Qwen3-8B", "downloads": 123456, "likes": 900, "pipeline_tag": "text-generation",
           "tags": ["safetensors", "qwen3", "tool-calling", "license:apache-2.0", "region:us"]},
          {"id": "secret/private", "private": True}, {"id": "gated/model", "gated": "manual"}, {"id": "bad id with spaces"}]
DATASETS = [{"id": "gorilla-llm/Berkeley-Function-Calling-Leaderboard", "description": "A live\n leaderboard.", "likes": 127,
             "tags": ["license:apache-2.0"]}]

CARD = "---\nlicense: apache-2.0\npipeline_tag: text-generation\n---\n# Qwen3-8B\n\n" + "A model card with real content about tool calling. " * 30


# ---- parsing -----------------------------------------------------------------------------------------

def test_hf_papers_become_arxiv_candidates_and_bad_records_are_skipped():
    out = f.parse_hf_papers(PAPERS)
    assert len(out) == 1
    p = out[0]
    assert (p.source, p.id) == ("arxiv", "2512.15943") and p.title == "Small Language Models for Tool Calling"
    assert p.url == "https://arxiv.org/pdf/2512.15943" and p.page_url == "https://arxiv.org/abs/2512.15943"
    assert p.authors == "A. One, B. Two" and p.published == "2025-12-17" and p.note == "found on Hugging Face Papers"
    assert f.parse_hf_papers("garbage") == [] and f.parse_hf_papers(None) == []


def test_hf_models_and_datasets_become_card_candidates_and_private_or_gated_are_skipped():
    models = f.parse_hf_repos(MODELS, 5, "model")
    assert [m.id for m in models] == ["Qwen/Qwen3-8B"]
    m = models[0]
    assert m.source == "hf-model" and m.title == "Qwen/Qwen3-8B (model card)"
    assert m.url == "https://huggingface.co/Qwen/Qwen3-8B/raw/main/README.md" and m.page_url == "https://huggingface.co/Qwen/Qwen3-8B"
    assert "apache-2.0" in m.licence and "downloads 123,456" in m.summary
    d = f.parse_hf_repos(DATASETS, 5, "dataset")[0]
    assert d.source == "hf-dataset" and "datasets/gorilla-llm" in d.url and d.summary == "A live leaderboard."
    assert len(f.parse_hf_repos(MODELS * 3, 1, "model")) == 1


# ---- the three searches ------------------------------------------------------------------------------

def routes(request):
    url = str(request.url)
    if url.endswith("robots.txt"):
        return httpx.Response(200, text="User-agent: *\nAllow: /")
    if "/api/papers/search" in url:
        return httpx.Response(200, json=PAPERS)
    if "/api/models" in url:
        return httpx.Response(200, json=MODELS)
    if "/api/datasets" in url:
        return httpx.Response(200, json=DATASETS)
    if url.endswith("/raw/main/README.md"):
        return httpx.Response(200, text=CARD + " Card of " + url)        # unique per repository (identical text is a duplicate)
    if "export.arxiv.org" in url or "europepmc" in url:
        return httpx.Response(200, json={"resultList": {"result": []}}) if "europepmc" in url else httpx.Response(
            200, text='<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"></feed>')
    return httpx.Response(404)


def test_the_searches_call_the_public_api_with_the_query():
    seen = []

    def handler(request):
        seen.append(request.url)
        return routes(request)

    fx, _ = make_fetcher(handler)
    assert fx.search_hf_papers("tool calling")[0].id == "2512.15943"
    assert fx.search_hf_models("tool calling", 3)[0].id == "Qwen/Qwen3-8B"
    assert fx.search_hf_datasets("function calling")[0].source == "hf-dataset"
    urls = [str(u) for u in seen if "robots" not in str(u)]
    assert any("q=tool+calling" in u or "q=tool%20calling" in u for u in urls)
    assert any("sort=downloads" in u and "limit=3" in u for u in urls)


# ---- discovery ---------------------------------------------------------------------------------------

JUDGE = lambda prompt, json_mode=False: json.dumps({"score": 3, "query": "tool calling"})  # noqa: E731


def test_discover_includes_hugging_face_papers_models_and_datasets(tmp_path):
    fx, _ = make_fetcher(routes)
    store = f.SourceStore(tmp_path / "Library", "goal")
    out = c.discover(["How do small models do tool calling?"], search=lambda q, n: [], fx=fx, store=store, llm=JUDGE,
                     huggingface=True)
    by_source = {d["source"]: d for d in out}
    assert {"arxiv", "hf-model", "hf-dataset"} <= set(by_source)
    assert by_source["arxiv"]["via"] == "found on Hugging Face Papers" and by_source["arxiv"]["kind"] == "paper"
    assert by_source["hf-model"]["kind"] == "page" and by_source["hf-model"]["site"] == "huggingface.co"
    off = c.discover(["How do small models do tool calling?"], search=lambda q, n: [], fx=fx, store=store, llm=JUDGE,
                     huggingface=False)
    assert not any(d["source"].startswith("hf-") for d in off)


def test_extra_ai_sites_are_searched_in_groups_of_six_with_site_filters(tmp_path):
    fx, _ = make_fetcher(routes)
    store = f.SourceStore(tmp_path / "Library", "goal")
    queries = []
    sites = [f"site{i}.example" for i in range(20)]               # more than the 18 used
    c.discover(["q?"], search=lambda q, n: queries.append(q) or [], fx=fx, store=store, llm=JUDGE, include_papers=False,
               extra_sites=sites)
    assert len(queries) == 4                                       # the plain search plus three site groups
    assert "site:site0.example OR site:site1.example" in queries[1] and "site:site5.example" in queries[1]
    assert "site:site6.example" in queries[2] and "site:site11.example" in queries[2]
    assert "site:site12.example" in queries[3] and "site:site17.example" in queries[3] and "site18" not in queries[3]
    queries.clear()
    c.discover(["q?"], search=lambda q, n: queries.append(q) or [], fx=fx, store=store, llm=JUDGE, include_papers=False)
    assert len(queries) == 1                                       # off by default in the function


def test_the_default_site_list_leads_with_the_explainer_blogs_in_their_own_group():
    sites = c.AI_SITES
    assert len(sites) == c.MAX_SITES == 18
    assert sites[:6] == ["sebastianraschka.com", "magazine.sebastianraschka.com", "karpathy.github.io", "karpathy.ai",
                         "jalammar.github.io", "newsletter.languagemodels.co"]
    assert Configuration().collect_extra_sites.split(";") == sites       # the setting and the constant agree


def test_a_failing_site_search_does_not_lose_the_main_results(tmp_path):
    fx, _ = make_fetcher(routes)
    store = f.SourceStore(tmp_path / "Library", "goal")

    def search(q, n):
        if "site:" in q:
            raise RuntimeError("rate limited")
        return [c.Hit("Main result page", "https://a.example/p", "x")]

    out = c.discover(["q?"], search=search, fx=fx, store=store, llm=JUDGE, include_papers=False, extra_sites=["x.example"])
    assert [d["title"] for d in out] == ["Main result page"]


# ---- collecting a card -------------------------------------------------------------------------------

def test_a_model_card_is_saved_as_markdown_without_its_yaml_header_and_with_provenance(tmp_path):
    fx, _ = make_fetcher(routes)
    store = f.SourceStore(tmp_path / "Library", "goal")
    cand = f.parse_hf_repos(MODELS, 5, "model")[0]
    cand.question = "q"
    summary = c.collect_selected([cand], store, fx)
    assert summary["saved"] == 1 and summary["pages"] == 1
    post = frontmatter.load(next(store.dir.glob("*.md")))
    assert post["url"] == "https://huggingface.co/Qwen/Qwen3-8B" and "apache-2.0" in post["licence"]
    assert post.content.lstrip().startswith("# Qwen3-8B") and "pipeline_tag" not in post.content


# ---- the limits are gone -----------------------------------------------------------------------------

def test_no_limit_by_default_in_settings():
    cfg = Configuration()
    assert cfg.fetch_max_sources == 0 and cfg.collect_max_candidates == 0
    assert cfg.collect_huggingface and cfg.collect_ai_sites and "huggingface.co" in cfg.collect_extra_sites


def test_collecting_has_no_limit_when_zero_or_none_and_still_obeys_a_positive_one(tmp_path):
    def run(limit):
        fx, _ = make_fetcher(routes)
        store = f.SourceStore(tmp_path / f"L{limit}", "goal")
        cands = []
        for i in range(12):
            cand = f.parse_hf_repos([{"id": f"org/model-{i}"}], 1, "model")[0]
            cand.question = "q"
            cands.append(cand)
        return c.collect_selected(cands, store, fx, max_sources=limit)["saved"]

    assert run(None) == 12 and run(0) == 12 and run(5) == 5


def test_model_search_retries_with_shorter_keywords_until_something_is_found():
    asked = []

    def finder(query, count):
        asked.append(query)
        return ["hit"] if query == "tool calling" else []

    out = c.shrinking(finder)("small language models for reliable tool calling", 2)
    assert out == ["hit"]
    assert asked == ["small language models for reliable tool calling", "reliable tool calling", "tool calling"]
    asked.clear()
    assert c.shrinking(lambda q, n: asked.append(q) or [])("one", 2) == [] and asked == ["one"]      # nothing to shrink


def test_europe_pmc_can_be_switched_off(tmp_path):
    asked = []

    def handler(request):
        asked.append(str(request.url))
        return routes(request)

    fx, _ = make_fetcher(handler)
    store = f.SourceStore(tmp_path / "Library", "goal")
    c.discover(["q?"], search=lambda q, n: [], fx=fx, store=store, llm=JUDGE, europepmc=False)
    assert not any("europepmc" in u for u in asked)
    assert Configuration().collect_europepmc is True
