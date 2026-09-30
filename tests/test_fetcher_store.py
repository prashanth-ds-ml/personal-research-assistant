"""SourceStore and collect(): dedupe keys, index durability, and unexpected records (audit follow-ups)."""

import json

import httpx
from tests_helpers import (  # noqa: F401  (shared fakes, see tests_helpers.py)
    fake_pdf_to_md,
    make_fetcher,
    ok_llm,
)

from research_assistant import fetcher as f


def cand(source="seed", id_="x", url="https://a.example/p", title="T"):
    return f.Candidate(source=source, id=id_, title=title, url=url, page_url=url)


def test_urls_that_differ_only_by_query_string_are_different_documents():
    assert f.normalize_url("https://x.org/p?id=1") != f.normalize_url("https://x.org/p?id=2")
    assert f.normalize_url("https://www.x.org/p/?b=2&a=1#top") == f.normalize_url("https://x.org/p?a=1&b=2")
    assert f.normalize_url("https://x.org/p?utm_source=mail&id=1") == f.normalize_url("https://x.org/p?id=1")


def test_the_same_filename_on_two_hosts_is_two_sources(tmp_path):
    store = f.SourceStore(tmp_path / "Library", "x")
    a = cand(id_="a-com-paper-pdf", url="https://a.com/paper.pdf")
    b = cand(id_="b-org-paper-pdf", url="https://b.org/paper.pdf")
    assert store.save(a, "alpha " * 300) is not None and store.save(b, "beta " * 300) is not None


def test_a_seed_pdf_id_includes_the_host(tmp_path):
    def handler(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"})

    fetcher, _ = make_fetcher(handler)
    a, _, _ = fetcher.fetch_seed("https://a.com/paper.pdf")
    b, _, _ = fetcher.fetch_seed("https://b.org/paper.pdf")
    assert a.id != b.id and "a-com" in a.id and "b-org" in b.id


def test_the_index_is_written_at_every_save_not_only_at_the_end(tmp_path):
    lib = tmp_path / "Library"
    store = f.SourceStore(lib, "x")
    store.save(cand(id_="one", url="https://a.example/1"), "text one " * 200)
    # no flush(): simulate a crash right here, then a new run
    again = f.SourceStore(lib, "y")
    assert again.seen(cand(id_="one", url="https://a.example/1")) is not None


def test_a_corrupt_index_is_set_aside_and_the_next_run_starts_fresh(tmp_path):
    lib = tmp_path / "Library"
    lib.mkdir()
    (lib / ".fetch_index.json").write_text('{"id:arxiv:1": "C:/x.md", "tor', encoding="utf-8")   # torn write
    store = f.SourceStore(lib, "x")                                            # must not raise
    assert store.index == {} and (lib / ".fetch_index.json.corrupt").exists()
    store.save(cand(id_="two", url="https://a.example/2"), "text two " * 200)
    assert json.loads((lib / ".fetch_index.json").read_text(encoding="utf-8"))


def test_the_index_file_is_replaced_atomically(tmp_path):
    lib = tmp_path / "Library"
    store = f.SourceStore(lib, "x")
    store.save(cand(id_="one", url="https://a.example/1"), "text one " * 200)
    assert not list(lib.glob("*.tmp"))                                         # no leftover temp file


def test_an_unexpected_record_shape_skips_that_source_instead_of_aborting(tmp_path):
    def handler(request):
        url = str(request.url)
        if "export.arxiv.org" in url:
            return httpx.Response(200, text="<feed xmlns='http://www.w3.org/2005/Atom'></feed>")
        if "europepmc/webservices/rest/search" in url:
            return httpx.Response(200, json={"resultList": {"result": [{"pmcid": "PMC1", "isOpenAccess": "Y", "title": 5}]}})
        return httpx.Response(404)

    fetcher, _ = make_fetcher(handler)
    store = f.SourceStore(tmp_path / "Library", "x")
    summary = f.collect(["q"], store, fetcher, ok_llm, convert_pdf=fake_pdf_to_md)    # a number where a title belongs
    assert summary["saved"] == 0 and summary["failed"] >= 1                     # recorded, and the run carried on
    assert (tmp_path / "Library" / "x" / "manifest.json").exists()
