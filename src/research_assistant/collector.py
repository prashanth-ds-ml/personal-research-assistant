"""The web collector: find candidate web pages and papers for the plan's questions, let the user choose, then
save the chosen ones as markdown in the library.

An independent agent with two calls, used by the deep-research graph and by ``scripts/collect.py``:

  discover(questions, ...)  -> candidates   searches and judges relevance; downloads nothing
  collect_selected(...)     -> summary      fetches the chosen candidates ONE AT A TIME, converts, saves

Everything that touches a website goes through ``Fetcher`` (public addresses only, redirects re-checked, robots.txt,
per-host delay, size cap). Links found inside a fetched page are never followed: candidates come only from search.
Design: docs/web-collector-design.md.
"""

import itertools
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from research_assistant import fetcher
from research_assistant.fetcher import Candidate, Fetcher, SourceStore

LLM = Callable[..., str]
PAPER_SOURCES = {"arxiv", "europepmc"}


@dataclass
class Hit:
    title: str
    url: str
    snippet: str = ""


Search = Callable[[str, int], list[Hit]]


# ---- search backends (a plain function each; the collector does not care which) --------------------------

def ddgs_search(query: str, n: int) -> list[Hit]:
    from ddgs import DDGS

    with DDGS() as d:
        rows = list(d.text(query, max_results=n))
    return [Hit(r.get("title") or "", r.get("href") or "", r.get("body") or "") for r in rows if r.get("href")]


def searxng_search(base_url: str, http: httpx.Client) -> Search:
    """Search through a SearXNG instance the user runs. The URL is configuration (environment only), so it is
    trusted like the arXiv API: it may be localhost."""
    def search(query: str, n: int) -> list[Hit]:
        r = http.get(base_url.rstrip("/") + "/search", params={"q": query, "format": "json"}, timeout=30)
        r.raise_for_status()
        rows = r.json().get("results", [])[:n]
        return [Hit(x.get("title") or "", x.get("url") or "", x.get("content") or "") for x in rows if x.get("url")]
    return search


def make_search(backend: str, searxng_url: str, http: httpx.Client) -> Search:
    if backend == "searxng" and searxng_url:
        return searxng_search(searxng_url, http)
    return ddgs_search


# ---- domain rules ---------------------------------------------------------------------------------------

def _host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _matches(host: str, pattern: str) -> bool:
    pattern = pattern.strip().lower().lstrip("*.").strip(".")
    return bool(pattern) and (host == pattern or host.endswith("." + pattern))


def domain_ok(url: str, allow: list[str], block: list[str]) -> bool:
    """Block-list first; then, if there is an allow-list, the host must match it (``who.int`` or ``*.gov.in``)."""
    host = _host(url)
    if not host or any(_matches(host, p) for p in block):
        return False
    return not allow or any(_matches(host, p) for p in allow)


def split_domains(text: str) -> list[str]:
    return [p.strip() for p in text.replace(",", ";").split(";") if p.strip()]


# ---- discover -------------------------------------------------------------------------------------------

def _web_candidate(hit: Hit, question: str) -> Candidate:
    host = _host(hit.url)
    return Candidate(source="web", id=fetcher.slugify(f"{host}-{hit.title or hit.url}"[:70]), title=hit.title or hit.url,
                     summary=hit.snippet, url=hit.url, page_url=hit.url, question=question,
                     licence="web page; private use")


def to_dict(c: Candidate, question_index: int) -> dict:
    """What the dashboard shows and sends back (the id is what the user ticks)."""
    return {"id": f"{c.source}:{c.id}", "title": c.title, "url": c.page_url or c.url, "site": _host(c.page_url or c.url),
            "kind": "paper" if c.source in PAPER_SOURCES or (c.page_url or c.url).lower().split("?")[0].endswith(".pdf")
            else "page", "question": c.question,
            "question_index": question_index, "score": c.relevance, "snippet": c.summary[:300], "source": c.source,
            "pdf_url": c.url if c.source == "arxiv" else "", "authors": c.authors, "published": c.published,
            "licence": c.licence}


def from_dict(d: dict) -> Candidate:
    source = d.get("source", "web")
    return Candidate(source=source, id=str(d["id"]).split(":", 1)[-1], title=d.get("title", ""),
                     summary=d.get("snippet", ""), url=d.get("pdf_url") or d.get("url", ""), page_url=d.get("url", ""),
                     authors=d.get("authors", ""), published=d.get("published", ""), licence=d.get("licence", ""),
                     relevance=int(d.get("score", -1)), question=d.get("question", ""))


def discover(questions: list[str], *, search: Search, fx: Fetcher, store: SourceStore, llm: LLM,
             per_question: int = 8, max_candidates: int = 40, min_score: int = 1, allow: list[str] | None = None,
             block: list[str] | None = None, include_papers: bool = True, search_pause: float = 1.0,
             question_indexes: list[int] | None = None,
             on_progress: Callable[[str], None] = lambda s: None) -> list[dict]:
    """Candidates for every question, one question at a time, each judged 0-3 for relevance. Returns dicts ready for
    the dashboard, best first within each question, anything scoring below ``min_score`` left out.
    Already-saved sources and URLs repeated across questions are dropped. ``question_indexes`` gives the plan's own
    number for each question when only some of them are searched (the dashboard groups candidates by that number)."""
    allow, block = allow or [], block or []
    seen_urls: set[str] = set()
    out: list[dict] = []
    # Each question gets an equal share of the total, so the first questions cannot use up the whole list.
    quota = max(1, -(-max_candidates // max(len(questions), 1)))
    for qi, q in enumerate(questions):
        if len(out) >= max_candidates:
            break
        qn = question_indexes[qi] if question_indexes else qi
        terms = fetcher.search_terms(q, llm)
        on_progress(f"Q{qn + 1}: searching for '{terms}'")
        groups: list[list[Candidate]] = []
        try:
            hits = search(terms, per_question * 2)             # ask for extra: some are filtered out below
            web = []
            for h in hits:
                key = fetcher.normalize_url(h.url)
                if key in seen_urls or not domain_ok(h.url, allow, block) or not h.url.startswith(("http://", "https://")):
                    continue
                seen_urls.add(key)
                web.append(_web_candidate(h, q))
            groups.append(web[:per_question])
        except Exception as e:                  # a search outage must not stop the run: papers may still be found
            on_progress(f"web search failed: {str(e)[:100]}")
        if include_papers:
            for label, finder in (("arXiv", fx.search_arxiv), ("Europe PMC", fx.search_europepmc)):
                try:
                    groups.append([c for c in finder(terms, 3) if domain_ok(c.page_url or c.url, allow, block)])
                except Exception as e:
                    on_progress(f"{label} search failed: {str(e)[:100]}")
        mixed = [c for group in itertools.zip_longest(*groups) for c in group if c is not None]
        found: list[dict] = []
        for c in mixed:
            c.question = q
            if store.seen(c):
                continue
            c.relevance = fetcher.triage(c, q, llm)
            if c.relevance >= min_score:
                found.append(to_dict(c, qn))
        found.sort(key=lambda d: -d["score"])
        on_progress(f"Q{qn + 1}: {len(found)} candidates worth showing")
        out.extend(found[: min(quota, max(0, max_candidates - len(out)))])
        fx.sleep(search_pause)                                  # be gentle with the search engine
    return out


# ---- collect --------------------------------------------------------------------------------------------

def fetch_one(c: Candidate, fx: Fetcher, convert_pdf: Callable[[bytes, str], str] | None) -> tuple[str, bytes | None, str]:
    """Returns (markdown, pdf_bytes_or_None, skip_reason). A non-empty reason means nothing usable was fetched."""
    if c.source == "europepmc":
        return fx.europepmc_fulltext(c.id), None, ""
    if c.source == "arxiv":
        resp = fx.get(c.url)
        resp.raise_for_status()
        if convert_pdf is None:
            return "", None, "PDF conversion not available"
        return convert_pdf(resp.content, c.id), resp.content, ""
    got, reason, raw = fx.fetch_seed(c.page_url or c.url)         # web page or PDF: robots, public address, size cap
    if got is None:
        return "", None, reason
    if c.source == "seed":                                       # a URL the user typed: take the real title and id
        c.title, c.id, c.authors, c.published = got.title, got.id, got.authors, got.published
    if raw is not None:
        if convert_pdf is None:
            return "", None, "PDF conversion not available"
        return convert_pdf(raw, c.id), raw, ""
    return got.full_text, None, ""


def collect_selected(candidates: list[Candidate], store: SourceStore, fx: Fetcher, *,
                     convert_pdf: Callable[[bytes, str], str] | None = None, max_sources: int = 20,
                     on_progress: Callable[[str], None] = lambda s: None) -> dict:
    """Fetch the chosen candidates one after another and save each as markdown. A source that fails is recorded and
    skipped. Returns the same summary shape as ``fetcher.collect`` plus how many were pages and how many papers."""
    saved = pages = papers = 0
    for i, c in enumerate(candidates):
        if saved >= max_sources:
            store.record(c, "skipped", f"limit of {max_sources} sources reached")
            continue
        on_progress(f"Fetching {i + 1}/{len(candidates)}: {c.title[:70]}")
        if store.seen(c):
            store.record(c, "skipped", "already in the library")
            continue
        try:
            text, raw, reason = fetch_one(c, fx, convert_pdf)
        except Exception as e:                                  # network, parse or conversion trouble: next one
            store.record(c, "failed", str(e)[:150])
            continue
        if reason:
            store.record(c, "skipped", reason)
            continue
        if len(text) < fetcher.MIN_TEXT_CHARS:
            store.record(c, "skipped", f"too little text ({len(text)} chars)")
            continue
        if store.save(c, text, raw):
            saved += 1
            if c.source in PAPER_SOURCES:
                papers += 1
            else:
                pages += 1
            on_progress(f"Saved: {c.title[:70]}")
    store.flush()
    by_status: dict[str, int] = {}
    for m in store.manifest:
        by_status[m["status"]] = by_status.get(m["status"], 0) + 1
    return {"saved": saved, "pages": pages, "papers": papers, "skipped": by_status.get("skipped", 0),
            "failed": by_status.get("failed", 0), "folder": str(store.dir)}
