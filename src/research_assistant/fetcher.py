"""A small, polite source fetcher: open-access papers and pages into the library folder.

NOT a general scraper. Sources, in order of preference:
  * arXiv API            (terms: at most one request per 3 seconds, one connection)
  * Europe PMC REST API  (no key; full text only for its open-access subset)
  * URLs the user supplies ("seeds"), fetched only if robots.txt allows it

Every candidate is scored for relevance by the local model BEFORE anything is downloaded, each
saved source carries provenance (where it came from, when, which question, a licence note), and
a manifest records every candidate with why it was kept or skipped. Content stays private.

HTTP, the clock and the model are injected so the rules are testable with no network.
"""

import hashlib
import ipaddress
import itertools
import json
import os
import re
import socket
import time
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib import robotparser
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlparse

import frontmatter
import httpx

LLM = Callable[..., str]

# Minimum seconds between requests, per RATE BUCKET. arXiv's terms say one request per 3 seconds for the
# API; its API host and PDF host share one bucket so an API call followed by a PDF fetch still obeys it.
RATE_BUCKET = {"export.arxiv.org": "arxiv", "arxiv.org": "arxiv", "www.arxiv.org": "arxiv"}
BUCKET_INTERVAL = {"arxiv": 3.0}
DEFAULT_INTERVAL = 1.0
MIN_TEXT_CHARS = 800          # less than this from a page usually means a login wall or an empty shell
MAX_BYTES = 40_000_000        # largest body we will download from a user-supplied URL (a long PDF is ~10 MB)
MAX_REDIRECTS = 5

_ARXIV_ID = re.compile(r"^[A-Za-z0-9.\-]+(/[A-Za-z0-9.\-]+)?$")
_PMCID = re.compile(r"^PMC\d+$")


class UnsafeURL(ValueError):
    """The URL is not one we will fetch (not http(s), or it points at a non-public address)."""


class TooLarge(ValueError):
    """The response body is bigger than the cap."""


def _default_resolve(host: str) -> list[str]:
    try:
        return sorted({info[4][0] for info in socket.getaddrinfo(host, None)})
    except OSError as e:
        raise UnsafeURL(f"cannot resolve {host}: {e}") from e


def user_agent(contact: str = "") -> str:
    who = f"contact: {contact}" if contact else "personal research tool"
    return f"ResearchAssistant/0.1 ({who})"


@dataclass
class Candidate:
    source: str                 # arxiv | europepmc | seed
    id: str
    title: str
    summary: str = ""
    url: str = ""               # where the content is fetched from (PDF or page)
    page_url: str = ""
    authors: str = ""
    published: str = ""
    licence: str = ""
    full_text: str = ""         # already-available text (Europe PMC JATS converted)
    relevance: int = -1
    question: str = ""
    note: str = ""


@dataclass
class Fetcher:
    http: httpx.Client
    contact: str = ""
    sleep: Callable[[float], None] = time.sleep
    now: Callable[[], float] = time.monotonic
    resolve: Callable[[str], list[str]] = _default_resolve
    _last: dict[str, float] = field(default_factory=dict)
    _robots: dict[str, robotparser.RobotFileParser | None] = field(default_factory=dict)

    # ---- politeness ---------------------------------------------------------

    def wait(self, host: str, extra: float = 0.0) -> None:
        """Block until the host's minimum interval has passed since our last request to it."""
        bucket = RATE_BUCKET.get(host, host)
        gap = max(BUCKET_INTERVAL.get(bucket, DEFAULT_INTERVAL), extra)
        last = self._last.get(bucket)
        if last is not None:
            remaining = gap - (self.now() - last)
            if remaining > 0:
                self.sleep(remaining)
        self._last[bucket] = self.now()

    def get(self, url: str, **kw) -> httpx.Response:
        """Fetch from a TRUSTED fixed host (the arXiv / Europe PMC APIs). Never use this for a
        user-supplied URL: see get_public."""
        host = urlparse(url).netloc
        for attempt in (1, 2):                      # one retry: a slow server is common, a dead one is not
            self.wait(host, extra=self.crawl_delay(url))
            try:
                return self.http.get(url, headers={"User-Agent": user_agent(self.contact)}, follow_redirects=True,
                                     timeout=30, **kw)
            except httpx.TimeoutException:
                if attempt == 2:
                    raise
        raise AssertionError("unreachable")

    # ---- safe fetching of user-supplied URLs --------------------------------

    def check_public(self, url: str) -> None:
        """Raise UnsafeURL unless the URL is http(s) and every address its host resolves to is public.
        Blocks localhost, private ranges, link-local (cloud metadata) and other non-global addresses."""
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.hostname:
            raise UnsafeURL("only http(s) URLs with a host name are allowed")
        if p.username or p.password:
            raise UnsafeURL("URLs with embedded credentials are not allowed")
        for ip in self.resolve(p.hostname):
            addr = ipaddress.ip_address(ip.split("%")[0])
            if addr.version == 6 and addr.ipv4_mapped:
                addr = addr.ipv4_mapped
            if not addr.is_global or addr.is_multicast:
                raise UnsafeURL(f"{p.hostname} resolves to a non-public address ({ip})")

    def get_public(self, url: str, max_bytes: int | None = None) -> httpx.Response:
        """GET a user-supplied URL safely: re-checks the address on EVERY redirect hop (a public URL can
        redirect to an internal one), streams the body with a byte cap, and never auto-follows."""
        max_bytes = max_bytes or MAX_BYTES
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            self.check_public(current)
            host = urlparse(current).netloc
            for attempt in (1, 2):
                self.wait(host, extra=self.crawl_delay(current))
                try:
                    with self.http.stream("GET", current, headers={"User-Agent": user_agent(self.contact)},
                                          follow_redirects=False, timeout=30) as r:
                        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                            current = urljoin(current, r.headers["location"])
                            break                                   # validate the next hop, then fetch it
                        buf = bytearray()
                        for chunk in r.iter_bytes():
                            buf += chunk
                            if len(buf) > max_bytes:
                                raise TooLarge(f"response is larger than {max_bytes // 1_000_000} MB")
                        headers = {k: v for k, v in r.headers.items()
                                   if k.lower() not in ("content-encoding", "content-length", "transfer-encoding")}
                        return httpx.Response(r.status_code, headers=headers, content=bytes(buf))
                except httpx.TimeoutException:
                    if attempt == 2:
                        raise
            else:
                continue
        raise UnsafeURL(f"more than {MAX_REDIRECTS} redirects")

    def _parser(self, url: str) -> robotparser.RobotFileParser | None:
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        if base not in self._robots:
            rp: robotparser.RobotFileParser | None = robotparser.RobotFileParser()
            try:
                r = self.get_public(f"{base}/robots.txt", max_bytes=500_000)
                if r.status_code >= 500:
                    rp = None                      # server error: be conservative and treat as disallowed
                elif r.status_code >= 400:
                    rp.parse([])                   # no robots.txt: everything allowed
                else:
                    rp.parse(r.text.splitlines())
            except (httpx.HTTPError, UnsafeURL, TooLarge):
                rp = None
            self._robots[base] = rp
        return self._robots[base]

    def allowed(self, url: str) -> bool:
        rp = self._parser(url)
        return bool(rp and rp.can_fetch(user_agent(self.contact), url))

    def crawl_delay(self, url: str) -> float:
        rp = self._robots.get(f"{urlparse(url).scheme}://{urlparse(url).netloc}")
        try:
            return float(rp.crawl_delay(user_agent(self.contact)) or 0) if rp else 0.0
        except (TypeError, ValueError):
            return 0.0

    # ---- official APIs ------------------------------------------------------

    def search_arxiv(self, query: str, n: int = 5) -> list[Candidate]:
        url = f"http://export.arxiv.org/api/query?search_query={quote(arxiv_query(query))}&max_results={n}&sortBy=relevance"
        r = self.get(url)
        r.raise_for_status()
        return parse_arxiv(r.text)

    def search_europepmc(self, query: str, n: int = 5) -> list[Candidate]:
        q = quote(f"({query}) AND OPEN_ACCESS:y")
        url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search?"
               f"query={q}&format=json&resultType=core&pageSize={n}")
        r = self.get(url)
        r.raise_for_status()
        return parse_europepmc(r.json())

    def europepmc_fulltext(self, pmcid: str) -> str:
        if not _PMCID.match(pmcid):
            raise ValueError(f"not a PMC id: {pmcid!r}")
        r = self.get(f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML")
        r.raise_for_status()
        return jats_to_markdown(r.text)

    # ---- seed URLs ----------------------------------------------------------

    def fetch_seed(self, url: str) -> tuple[Candidate | None, str, bytes | None]:
        """Returns (candidate, reason_if_skipped, raw_pdf_bytes). Skips what robots.txt forbids and
        anything that is not a public http(s) address."""
        try:
            self.check_public(url)
            if not self.allowed(url):
                return None, "blocked by robots.txt (or robots.txt unreachable)", None
            r = self.get_public(url)
        except UnsafeURL as e:
            return None, f"blocked: {e}", None
        except TooLarge as e:
            return None, f"skipped: {e}", None
        if r.status_code in (401, 402, 403):
            return None, f"HTTP {r.status_code}: login or paywall", None
        if r.status_code >= 400:
            return None, f"HTTP {r.status_code}", None
        ctype = r.headers.get("content-type", "")
        path = urlparse(url).path
        seed_id = slugify(f"{urlparse(url).netloc}-{path.rsplit('/', 1)[-1] or 'index'}")
        if "pdf" in ctype or path.lower().endswith(".pdf"):
            return Candidate(source="seed", id=seed_id, title=url, url=url, page_url=url,
                             licence="user-supplied URL; private use"), "", r.content
        import trafilatura

        text = trafilatura.extract(r.text, output_format="markdown", include_tables=True, include_links=False,
                                   url=url, favor_precision=True) or ""
        if len(text) < MIN_TEXT_CHARS:
            return None, f"too little text ({len(text)} chars): empty page or login wall", None
        meta = trafilatura.extract_metadata(r.text, default_url=url)
        title = (meta.title if meta and meta.title else url)
        return Candidate(source="seed", id=slugify(f"{urlparse(url).netloc}-{title}"[:70]), title=title, url=url,
                         page_url=url, authors=(meta.author or "") if meta else "",
                         published=(meta.date or "") if meta else "", licence="web page; private use",
                         full_text=text), "", None


# ---- parsing (pure functions, tested with canned responses) --------------------------------

_ATOM = {"a": "http://www.w3.org/2005/Atom"}


def slugify(text: str, max_len: int = 70) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:max_len] or "source"


def arxiv_query(terms: str, max_terms: int = 5) -> str:
    """'hybrid retrieval augmented generation' -> 'all:hybrid AND all:retrieval AND ...'.
    (arXiv only applies the 'all:' field to the first word of an unquoted multi-word query.)"""
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9-]*", terms)[:max_terms]
    return " AND ".join(f"all:{w}" for w in words) or f"all:{terms}"


def parse_arxiv(xml_text: str) -> list[Candidate]:
    out = []
    for e in ET.fromstring(xml_text).findall("a:entry", _ATOM):
        abs_url = (e.findtext("a:id", "", _ATOM) or "").strip()
        aid = abs_url.rsplit("/abs/", 1)[-1]
        title = re.sub(r"\s+", " ", e.findtext("a:title", "", _ATOM) or "").strip()
        if not aid or not title or "/api/errors" in abs_url or not _ARXIV_ID.match(aid):
            continue                      # error feed entry, or an id we will not put into a URL
        out.append(Candidate(
            source="arxiv", id=aid, title=title,
            summary=re.sub(r"\s+", " ", e.findtext("a:summary", "", _ATOM) or "").strip(),
            url=f"https://arxiv.org/pdf/{aid}", page_url=abs_url,
            authors=", ".join(a.findtext("a:name", "", _ATOM) for a in e.findall("a:author", _ATOM)),
            published=(e.findtext("a:published", "", _ATOM) or "")[:10],
            licence="arXiv; licence varies by paper; private use only"))
    return out


def parse_europepmc(payload: dict) -> list[Candidate]:
    out = []
    for r in (payload.get("resultList") or {}).get("result", []):
        pmcid = r.get("pmcid")
        if not pmcid or not _PMCID.match(str(pmcid)) or r.get("isOpenAccess") != "Y":
            continue                      # no legal full text (or a malformed id): skip rather than guess
        out.append(Candidate(
            source="europepmc", id=pmcid, title=re.sub(r"<[^>]+>", "", r.get("title") or "").strip() or pmcid,
            summary=re.sub(r"<[^>]+>", "", r.get("abstractText") or "").strip(),
            page_url=f"https://europepmc.org/article/{r.get('source', 'PMC')}/{r.get('id', pmcid)}",
            authors=r.get("authorString") or "", published=str(r.get("firstPublicationDate") or r.get("pubYear") or ""),
            licence=f"Europe PMC open access ({r.get('license', 'licence not stated')}); private use"))
    return out


def _text(el: ET.Element) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def jats_to_markdown(xml_text: str) -> str:
    """Europe PMC full-text XML (JATS) -> markdown: title, abstract, sections, simple tables."""
    root = ET.fromstring(xml_text)
    lines: list[str] = []
    title = root.find(".//article-title")
    if title is not None:
        lines += [f"# {_text(title)}", ""]
    abstract = root.find(".//abstract")
    if abstract is not None:
        lines += ["## Abstract", "", _text(abstract), ""]

    def walk(sec: ET.Element, depth: int) -> None:
        t = sec.find("title")
        if t is not None:
            lines.extend([f"{'#' * min(depth + 1, 6)} {_text(t)}", ""])
        for child in sec:
            if child.tag == "p":
                lines.extend([_text(child), ""])
            elif child.tag == "sec":
                walk(child, depth + 1)
            elif child.tag == "table-wrap":
                cap = child.find(".//caption")
                if cap is not None:
                    lines.extend([f"**{_text(cap)}**", ""])
                rows = [[_text(c) for c in tr if c.tag in ("th", "td")] for tr in child.iter("tr")]
                rows = [r for r in rows if r]
                if rows:
                    width = max(len(r) for r in rows)
                    norm = [r + [""] * (width - len(r)) for r in rows]
                    lines.append("| " + " | ".join(norm[0]) + " |")
                    lines.append("|" + "---|" * width)
                    lines.extend("| " + " | ".join(r) + " |" for r in norm[1:])
                    lines.append("")

    body = root.find(".//body")
    if body is not None:
        for sec in body.findall("sec"):
            walk(sec, 1)
        for p in body.findall("p"):
            lines.extend([_text(p), ""])
    return "\n".join(lines).strip() + "\n"


# ---- triage ------------------------------------------------------------------------

TRIAGE_PROMPT = """Question a researcher is trying to answer: {question}

Candidate source:
Title: {title}
Abstract: {summary}

How useful is this source for answering the question?
0 = unrelated, 1 = loosely related, 2 = relevant, 3 = directly answers it.
Return JSON: {{"score": 0-3}}"""

TERMS_PROMPT = """Turn this research question into a short keyword search query (3-6 words, no operators, no quotes)
that would find relevant papers. Question: {question}
Return JSON: {{"query": "..."}}"""


def _json(text: str, default):
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text or "", re.S)
        try:
            return json.loads(m.group(0)) if m else default
        except Exception:
            return default


def search_terms(question: str, llm: LLM) -> str:
    raw = _json(llm(TERMS_PROMPT.format(question=question), json_mode=True), {})
    q = raw.get("query") if isinstance(raw, dict) else None
    if isinstance(q, str) and q.strip():
        return q.strip()
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z-]{3,}", question) if w.lower() not in _STOP]
    return " ".join(words[:6])


_STOP = {"what", "which", "that", "this", "with", "from", "have", "does", "about", "their", "there", "these",
         "those", "were", "when", "where", "while", "would", "could", "should", "into", "such", "than", "them"}


def triage(c: Candidate, question: str, llm: LLM) -> int:
    raw = _json(llm(TRIAGE_PROMPT.format(question=question, title=c.title, summary=c.summary[:900]), json_mode=True), {})
    try:
        return max(0, min(3, int(raw.get("score", 0) if isinstance(raw, dict) else 0)))
    except (TypeError, ValueError):
        return 0


# ---- saving + dedupe + manifest ------------------------------------------------------

_TRACKING = ("utm_", "fbclid", "gclid", "mc_", "ref", "source")


_ARXIV_URL = re.compile(r"arxiv\.org/(?:abs|pdf)/((?:[a-z\-]+(?:\.[A-Z]{2})?/\d{7})|(?:\d{4}\.\d{4,5}))(?:v\d+)?(?:\.pdf)?", re.I)


def arxiv_key(text: str) -> str | None:
    """"arxiv:<id>" (version removed) for an arXiv address of any kind (abs page, pdf link), else None. The same paper reached
    through the web search (abs page) and through the arXiv search (pdf) then counts as ONE source."""
    m = _ARXIV_URL.search(text or "")
    return f"arxiv:{m.group(1).lower()}" if m else None


def normalize_url(url: str) -> str:
    """A stable key for 'the same page': host without www, path without trailing slash, the query string
    (sorted, tracking parameters removed) and no fragment. The query matters: ?id=1 and ?id=2 are
    different documents on many sites."""
    p = urlparse(url.strip())
    query = sorted((k, v) for k, v in parse_qsl(p.query) if not k.lower().startswith(_TRACKING))
    base = f"{p.netloc.lower().removeprefix('www.')}{p.path.rstrip('/')}".lower()
    return f"{base}?{urlencode(query)}" if query else base


class SourceStore:
    """Saves sources under <library>/<goal-slug>/ and remembers what it has (by id, URL and content
    hash) across runs in <library>/.fetch_index.json, so the same paper is never saved twice."""

    def __init__(self, library_dir: Path, goal_slug: str):
        self.dir = Path(library_dir) / goal_slug
        self.index_path = Path(library_dir) / ".fetch_index.json"
        self.index: dict[str, str] = self._load_index()
        self.manifest: list[dict] = []

    def _load_index(self) -> dict[str, str]:
        """Read the index; a torn or corrupt file is set aside (not fatal for every later run)."""
        if not self.index_path.exists():
            return {}
        try:
            data = json.loads(self.index_path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, OSError, UnicodeDecodeError):
            pass
        try:
            os.replace(self.index_path, self.index_path.with_suffix(".json.corrupt"))
        except OSError:
            pass
        return {}

    def _write_index(self) -> None:
        """Atomic write: a crash mid-write leaves the old index, never half of a new one."""
        tmp = self.index_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(self.index, indent=1), encoding="utf-8")
        os.replace(tmp, self.index_path)

    def _keys(self, c: Candidate, text: str = "") -> list[str]:
        keys = [f"id:{c.source}:{c.id}"]
        if c.page_url or c.url:
            keys.append("url:" + normalize_url(c.page_url or c.url))
        paper = arxiv_key(c.page_url or c.url) or (arxiv_key(f"arxiv.org/abs/{c.id}") if c.source == "arxiv" else None)
        if paper:
            keys.append(paper)
        if text:
            keys.append("hash:" + hashlib.sha256(text.encode("utf-8")).hexdigest())
        return keys

    def seen(self, c: Candidate) -> str | None:
        """Path of the saved copy, if we have one. An entry whose file was deleted is forgotten, so
        removing a source from the library lets it be fetched again."""
        for k in self._keys(c):
            path = self.index.get(k)
            if path and Path(path).exists():
                return path
            if path:
                self.index.pop(k, None)
        return None

    def record(self, c: Candidate, status: str, reason: str = "", path: str = "") -> None:
        self.manifest.append({"source": c.source, "id": c.id, "title": c.title, "url": c.page_url or c.url,
                              "question": c.question, "relevance": c.relevance, "status": status,
                              "reason": reason, "file": path})

    def save(self, c: Candidate, markdown: str, raw: bytes | None = None) -> str | None:
        """Write markdown (+ original PDF). Returns the file path, or None if it is a duplicate."""
        dup = self.seen(c) or next((self.index[k] for k in self._keys(c, markdown)
                                    if k in self.index and Path(self.index[k]).exists()), None)
        if dup:
            self.record(c, "skipped", f"duplicate of {dup}")
            return None
        self.dir.mkdir(parents=True, exist_ok=True)
        name = slugify(f"{c.id}-{c.title}")
        if raw:
            (self.dir / "raw").mkdir(exist_ok=True)
            (self.dir / "raw" / f"{name}.pdf").write_bytes(raw)
        post = frontmatter.Post(
            markdown, title=c.title, source=c.source, source_id=c.id, url=c.page_url or c.url, authors=c.authors,
            published=c.published, licence=c.licence, question=c.question, relevance=c.relevance,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            content_hash=hashlib.sha256(markdown.encode("utf-8")).hexdigest())
        path = self.dir / f"{name}.md"
        path.write_text(frontmatter.dumps(post), encoding="utf-8")
        for k in self._keys(c, markdown):
            self.index[k] = str(path)
        self._write_index()                 # per save, so a crash later in the run cannot cause duplicates
        self.record(c, "saved", path=str(path))
        return str(path)

    def flush(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / "manifest.json").write_text(json.dumps(self.manifest, indent=1), encoding="utf-8")
        self._write_index()


# ---- the whole job -----------------------------------------------------------------

def collect(questions: list[str], store: SourceStore, fetcher: Fetcher, llm: LLM, *, seeds: list[str] | None = None,
            max_sources: int = 10, per_source_results: int = 5, keep_score: int = 3,
            convert_pdf: Callable[[bytes, str], str] | None = None,
            on_progress: Callable[[str], None] = lambda s: None) -> dict:
    """Find, triage, fetch and save sources for these questions. Returns the manifest summary.

    ``convert_pdf(pdf_bytes, name) -> markdown`` turns a downloaded PDF into text (Docling in
    production). A failing source is recorded and skipped, never fatal."""
    saved = 0

    def room() -> bool:
        return saved < max_sources

    for url in seeds or []:
        if not room():
            break
        try:
            cand, reason, raw = fetcher.fetch_seed(url)
        except httpx.HTTPError as e:
            store.record(Candidate(source="seed", id=slugify(url), title=url, url=url), "failed", str(e)[:150])
            continue
        if cand is None:
            store.record(Candidate(source="seed", id=slugify(url), title=url, url=url), "skipped", reason)
            continue
        text = cand.full_text
        if raw is not None:
            if convert_pdf is None:
                store.record(cand, "skipped", "PDF conversion not available")
                continue
            try:
                text = convert_pdf(raw, cand.id)
            except Exception as e:
                store.record(cand, "failed", f"PDF conversion failed: {str(e)[:120]}")
                continue
        if store.save(cand, text, raw):
            saved += 1
            on_progress(f"saved seed: {cand.title[:70]}")

    for q in questions:
        if not room():
            break
        terms = search_terms(q, llm)
        on_progress(f"searching for: {terms}")
        per_source: list[list[Candidate]] = []
        for label, search in (("arXiv", fetcher.search_arxiv), ("Europe PMC", fetcher.search_europepmc)):
            try:
                per_source.append(search(terms, per_source_results))
            except Exception as e:          # an HTTP error, bad XML/JSON, or an unexpected record: skip this source
                store.record(Candidate(source=label.lower(), id="search", title=f"{label} search: {terms}"),
                             "failed", str(e)[:150])
        # Alternate between sources so a small cap is shared instead of filled by whichever comes first.
        candidates = [c for group in itertools.zip_longest(*per_source) for c in group if c is not None]
        for c in candidates:
            if not room():
                break
            c.question = q
            if store.seen(c):
                store.record(c, "skipped", "already in the library")
                continue
            c.relevance = triage(c, q, llm)
            if c.relevance < keep_score:
                store.record(c, "skipped", f"relevance {c.relevance} < {keep_score}")
                continue
            try:
                if c.source == "arxiv":
                    resp = fetcher.get(c.url)
                    resp.raise_for_status()
                    if convert_pdf is None:
                        store.record(c, "skipped", "PDF conversion not available")
                        continue
                    text, raw = convert_pdf(resp.content, c.id), resp.content
                else:
                    text, raw = fetcher.europepmc_fulltext(c.id), None
            except Exception as e:
                store.record(c, "failed", str(e)[:150])
                continue
            if len(text) < MIN_TEXT_CHARS:
                store.record(c, "skipped", f"too little text ({len(text)} chars)")
                continue
            if store.save(c, text, raw):
                saved += 1
                on_progress(f"saved: {c.title[:70]}")
    store.flush()
    by_status: dict[str, int] = {}
    for m in store.manifest:
        by_status[m["status"]] = by_status.get(m["status"], 0) + 1
    return {"saved": saved, "skipped": by_status.get("skipped", 0), "failed": by_status.get("failed", 0),
            "folder": str(store.dir)}
