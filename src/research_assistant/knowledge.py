"""Persistent knowledge base: the RAG layer under every research run.

Documents (PDF/DOCX/HTML via Docling, Markdown/text directly) are converted to
markdown, chunked along their headings (tables are kept whole up to a size limit, then split by
rows with the header repeated), embedded, and stored in one SQLite file:

  * ``chunks_fts``  - FTS5/BM25 keyword index (exact terms, drug names, IDs)
  * ``chunks.embedding`` - float32 vectors for semantic search
  * ``docs.markdown`` - the converted text, so the library can be re-chunked or re-embedded
    (new embedding model, better chunker) without converting every PDF again

``search`` fuses both rankings with reciprocal-rank fusion, which beats either
alone on real corpora (keywords catch what embeddings blur and vice versa).
Ingestion is incremental: a file is re-processed only when its content hash
changes, so the folder can keep growing without re-embedding everything. The embedding model
and vector size are recorded; opening the library with a different model raises
``EmbeddingMismatch`` instead of silently mixing incompatible vectors.
"""

import hashlib
import re
import sqlite3
import struct
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import frontmatter
import numpy as np

# Folders never indexed: the fetcher keeps the ORIGINAL PDFs in raw/ next to the converted markdown.
SKIP_DIRS = {"raw", ".kb"}
KB_EXTENSIONS = (".pdf", ".docx", ".pptx", ".html", ".htm", ".md", ".markdown", ".txt")
CONVERT_WITH_DOCLING = (".pdf", ".docx", ".pptx", ".html", ".htm")

MAX_CHUNK_CHARS = 1800          # text chunks
MAX_TABLE_CHARS = 3000          # a table chunk: bigger tables are split by rows (header repeated)
# Locked 2026-10-19 (Test A, EVALS "v3 chunk size"): every document in a library is cut with the same settings. The
# library records this string and refuses to mix (like the embedding model); change it only with a full rebuild.
CHUNKER = f"v2 text={MAX_CHUNK_CHARS} table={MAX_TABLE_CHARS}"
MAX_HEADING_CHARS = 300        # the heading path prefixed to each chunk (part of CHUNKER v2)
EMBED_BATCH = 32                # chunks per embedding request: one request per whole document made Ollama's runner fail
MIN_CHUNK_CHARS = 40            # a text chunk shorter than this (a bare caption or heading) is noise

SCHEMA = """
CREATE TABLE IF NOT EXISTS docs (
    id INTEGER PRIMARY KEY, path TEXT UNIQUE, hash TEXT, title TEXT,
    source_url TEXT, ingested_at TEXT, n_chunks INTEGER,
    status TEXT DEFAULT 'ok', error TEXT DEFAULT '', markdown TEXT
);
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY, doc_id INTEGER REFERENCES docs(id) ON DELETE CASCADE,
    ord INTEGER, heading TEXT, page INTEGER, kind TEXT, text TEXT, embedding BLOB
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    text, heading, content='chunks', content_rowid='id', tokenize='porter unicode61'
);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""
# docs columns added after the first release: added to existing databases on open.
MIGRATIONS = {"status": "TEXT DEFAULT 'ok'", "error": "TEXT DEFAULT ''", "markdown": "TEXT",
              "source_kind": "TEXT DEFAULT ''"}


class ChunkerMismatch(RuntimeError):
    """The library was chunked with different settings than the code now uses."""


class EmbeddingMismatch(RuntimeError):
    """The library was built with a different embedding model (or vector size) than the one in use."""


def default_kb_path(vault_path: str = "") -> str:
    """Single source of truth for where the library lives: KB_PATH if set, else
    <vault>/.kb/library.sqlite. Used by the graph AND the scripts so they agree."""
    import os

    if os.environ.get("KB_PATH"):
        return os.environ["KB_PATH"]
    vault = vault_path or os.environ.get("VAULT_PATH", "")
    return str(Path(vault or ".") / ".kb" / "library.sqlite")


def folder_namespaces(paths: list[Path]) -> dict[Path, str]:
    """Namespace (prefix of every document key) for each folder: its name, unless two different folders
    share a name, in which case each gets the name plus a short hash of its full path. Without this, two
    folders called 'Papers' would prune each other's documents on every ingest. The same folder listed
    twice is not a clash."""
    resolved = list(dict.fromkeys(p.resolve() for p in paths))
    names = [p.name for p in resolved]
    return {p: (p.name if names.count(p.name) == 1 else f"{p.name}-{hashlib.sha1(str(p).encode()).hexdigest()[:6]}")
            for p in resolved}


# ---- conversion -----------------------------------------------------------

_DOCLING_CONVERTERS: dict[bool, object] = {}

# A born-digital page yields well over this many characters; a scanned page
# converted without OCR yields almost none.
MIN_CHARS_PER_PAGE = 100


def _docling_converter(ocr: bool):
    """Cached Docling converters. OCR is OFF by default: for born-digital PDFs it
    is most of the conversion time (measured 77 s -> 21 s on one paper with
    byte-identical output)."""
    if ocr not in _DOCLING_CONVERTERS:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption

        opts = PdfPipelineOptions()
        opts.do_ocr = ocr
        _DOCLING_CONVERTERS[ocr] = DocumentConverter(
            format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opts)})
    return _DOCLING_CONVERTERS[ocr]


def convert_with_ocr_fallback(path: Path, get_converter=_docling_converter) -> str:
    """Convert without OCR; if the result is nearly empty for its page count the
    PDF is scanned, so convert again with OCR."""
    doc = get_converter(False).convert(str(path)).document
    md = doc.export_to_markdown()
    pages = max(len(getattr(doc, "pages", []) or []), 1)
    if len(md.strip()) < MIN_CHARS_PER_PAGE * pages and path.suffix.lower() == ".pdf":
        md = get_converter(True).convert(str(path)).document.export_to_markdown()
    return md


def convert_to_markdown(path: Path) -> str:
    """File -> markdown. Docling for rich formats (keeps tables as markdown
    tables); plain read for md/txt. Falls back to pypdf text for PDFs if
    Docling is not installed."""
    suffix = path.suffix.lower()
    if suffix not in CONVERT_WITH_DOCLING:
        return path.read_text(encoding="utf-8", errors="replace")
    try:
        return convert_with_ocr_fallback(path)
    except ImportError:
        if suffix != ".pdf":
            raise
        from pypdf import PdfReader

        pages = (p.extract_text() or "" for p in PdfReader(str(path)).pages)
        return "\n\n".join(f"<!-- page {i} -->\n{t}" for i, t in enumerate(pages, 1) if t.strip())


def split_front_matter(text: str) -> tuple[dict, str]:
    """(metadata, body) of a markdown file that starts with a YAML block; ({}, text) when it does not.
    Saved sources carry provenance there (url, source, the question they were found for). That block is metadata, not
    content: indexing it made a source match the very question that fetched it."""
    if not text.startswith("---"):
        return {}, text
    try:
        post = frontmatter.loads(text)
        return dict(post.metadata), post.content
    except Exception:
        return {}, text


def classify_source(path: str, front: dict) -> tuple[str, str]:
    """(kind, url) of a document, so reports and the dashboard can tell PDFs from web pages.

    kind is "pdf" (a PDF file, an arXiv paper, or a PDF address), "paper" (open-access full text without a PDF),
    "web" (a web page) or "document" (anything else, for example a note or a locally archived page)."""
    suffix = Path(path).suffix.lower()
    source = str(front.get("source", "")).lower()
    url = str(front.get("url", "") or "")
    if not url.startswith(("http://", "https://")):
        url = ""
    if source == "arxiv":
        sid = str(front.get("source_id", ""))
        return "pdf", url or (f"https://arxiv.org/abs/{sid}" if sid else "")
    if source == "europepmc":
        return "paper", url
    if suffix == ".pdf" or url.lower().split("?")[0].endswith(".pdf"):
        return "pdf", url
    if source in ("web", "seed") or url:
        return "web", url
    return "document", ""


_TITLE = re.compile(r"^#{1,3}\s+(.{8,200})$")


def title_from_markdown(md: str, fallback: str) -> str:
    """First markdown heading (Docling puts the paper title there), else fallback."""
    for line in md.splitlines()[:40]:
        m = _TITLE.match(line.strip())
        if m:
            return m.group(1).strip()
    return fallback


# ---- chunking -------------------------------------------------------------

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_TABLE_LINE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_RULE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
_PAGE_MARK = re.compile(r"<!--\s*page\s+(\d+)\s*-->")

# Sections that only add retrieval noise (bibliographies etc.). Anchored: the heading must BE one of these
# (optionally numbered), so "Cross-references in practice" or "References to prior work" are kept.
SKIP_SECTIONS = re.compile(
    r"^\s*(?:[\dA-Za-z]{1,3}[.)]?\s+)?(references|bibliography|works cited|acknowledg(?:e)?ments?)\s*:?\s*$", re.I)


def _split_table(rows: list[str], max_chars: int) -> list[str]:
    """One table -> pieces of at most ``max_chars``, each starting with the header row (and its rule line)."""
    text = "\n".join(rows)
    if len(text) <= max_chars:
        return [text]
    header = rows[:2] if len(rows) > 1 and _TABLE_RULE.match(rows[1]) else rows[:1]
    body = rows[len(header):]
    # The header repeats in every piece, so it may use at most a third of a piece: a 2,332-character header line made
    # every piece of one table 7,159 characters (2026-10-19).
    room = max_chars // 3 // len(header)
    header = [r[:room] for r in header]
    head_len = sum(len(r) + 1 for r in header)
    pieces, cur, size = [], [], head_len
    for row in body:
        if cur and size + len(row) + 1 > max_chars:
            pieces.append("\n".join(header + cur))
            cur, size = [], head_len
        # a single row longer than the limit is cut (a row is cells of text, not a structure we can keep)
        cur.append(row[:max_chars - head_len - 1])
        size += len(cur[-1]) + 1
    if cur:
        pieces.append("\n".join(header + cur))
    return pieces


def chunk_markdown(md: str, max_chars: int = MAX_CHUNK_CHARS, max_table_chars: int = MAX_TABLE_CHARS) -> list[dict]:
    """Split markdown into chunks: {heading, page, kind, text}.

    Splits on headings, then on paragraph boundaries under ``max_chars``. A markdown table stays whole
    (kind="table") up to ``max_table_chars``; a bigger table is split by rows with its header repeated in
    every piece (a 80,000-character table chunk cannot be embedded or shown to a model). Each chunk is
    prefixed with its heading path so it is meaningful on its own when retrieved. Reference lists and
    bare captions are dropped.
    """
    chunks: list[dict] = []
    trail: list[str] = []
    page = 1
    buf: list[str] = []

    def heading_path() -> str:
        # capped: a broken PDF heading of 2,190 characters was repeated at the top of every chunk under it
        path = " > ".join(trail)
        return path if len(path) <= MAX_HEADING_CHARS else path[:MAX_HEADING_CHARS].rsplit(" ", 1)[0] + " ..."

    def flush():
        text = "\n".join(buf).strip()
        buf.clear()
        if not text:
            return
        # Pack paragraphs up to max_chars.
        paras, cur = re.split(r"\n{2,}", text), ""
        for para in paras:
            if cur and len(cur) + len(para) + 2 > max_chars:
                chunks.append({"heading": heading_path(), "page": page, "kind": "text", "text": cur})
                cur = ""
            while len(para) > max_chars:  # one giant paragraph
                chunks.append({"heading": heading_path(), "page": page, "kind": "text", "text": para[:max_chars]})
                para = para[max_chars:]
            cur = f"{cur}\n\n{para}" if cur else para
        if cur.strip():
            chunks.append({"heading": heading_path(), "page": page, "kind": "text", "text": cur})

    lines = md.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if m := _PAGE_MARK.search(line):
            flush()                      # text before the marker belongs to the previous page
            page = int(m.group(1))
            i += 1
            continue
        if h := _HEADING.match(line):
            flush()
            level = len(h.group(1))
            trail[:] = [*trail[: level - 1], h.group(2).strip()]
            i += 1
            continue
        if _TABLE_LINE.match(line):
            flush()
            table = []
            while i < len(lines) and _TABLE_LINE.match(lines[i]):
                table.append(lines[i])
                i += 1
            for piece in _split_table(table, max_table_chars):
                chunks.append({"heading": heading_path(), "page": page, "kind": "table", "text": piece})
            continue
        buf.append(line)
        i += 1
    flush()

    chunks = [c for c in chunks if not SKIP_SECTIONS.match(c["heading"].split(" > ")[-1])]
    # Drop bare captions and stubs, but only when the document has real content beside them: a document
    # that consists of one short note must still be searchable.
    substantial = [c for c in chunks if not (c["kind"] == "text" and len(c["text"].strip()) < MIN_CHUNK_CHARS)]
    chunks = substantial or chunks
    for c in chunks:
        if c["heading"]:
            c["text"] = f"[{c['heading']}]\n{c['text']}"
    return chunks


# ---- store ----------------------------------------------------------------

def _pack(vec) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def _unpack(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def _fts_query(query: str) -> str:
    words = re.findall(r"[\w-]{2,}", query.lower())
    return " OR ".join(f'"{w}"' for w in words)


class KnowledgeBase:
    def __init__(self, db_path: str | Path, embeddings, embedding_model: str = ""):
        """``embedding_model`` (the configured model string) is recorded on first use and checked on every
        later open; leave it empty to skip the check (tests, or when rebuilding with ``rebuild``)."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.embeddings = embeddings
        self._lock = threading.RLock()
        # timeout = how long to wait for another connection's write lock instead of failing at once
        self.db = sqlite3.connect(self.db_path, check_same_thread=False, timeout=30)
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)
        self._migrate()
        self._matrix_cache: tuple | None = None
        self._check_model(embedding_model)
        self._check_chunker()

    # -- lifecycle --

    def close(self) -> None:
        with self._lock:
            try:
                self.db.close()
            except sqlite3.Error:
                pass

    def __enter__(self) -> "KnowledgeBase":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def _migrate(self) -> None:
        have = {r[1] for r in self.db.execute("PRAGMA table_info(docs)")}
        for col, ddl in MIGRATIONS.items():
            if col not in have:
                self.db.execute(f"ALTER TABLE docs ADD COLUMN {col} {ddl}")
        self.db.commit()

    # -- metadata: embedding model, vector size, write generation --

    def _meta(self, key: str) -> str | None:
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def _set_meta(self, key: str, value: str) -> None:
        self.db.execute("INSERT INTO meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (key, value))

    def _bump_generation(self) -> None:
        self._set_meta("generation", str(int(self._meta("generation") or 0) + 1))

    def _check_model(self, model: str) -> None:
        stored = self._meta("embedding_model")
        if model and stored and stored != model:
            raise EmbeddingMismatch(
                f"This library was built with embedding model '{stored}' but '{model}' is configured. Mixing "
                "them makes search wrong. Either set EMBEDDING_MODEL back, or re-embed the library with "
                "`python scripts/reindex.py --rebuild` (it keeps the converted text, so PDFs are not converted again).")
        if model and not stored:
            # A new library records its model at once; a legacy library (built before models were recorded)
            # adopts the configured one, along with the vector size its chunks already have.
            self._set_meta("embedding_model", model)
            existing = self.db.execute("SELECT length(embedding)/4 FROM chunks LIMIT 1").fetchone()
            if existing and not self._meta("embedding_dim"):
                self._set_meta("embedding_dim", str(existing[0]))
            self.db.commit()

    def _check_chunker(self) -> None:
        """Every document in one library is cut the same way. A new library records the chunker settings; one built
        with other settings refuses to take new documents until it is rebuilt (an old library without a record is
        recorded by its next rebuild)."""
        stored = self._meta("chunker")
        if stored and stored != CHUNKER:
            raise ChunkerMismatch(
                f"This library was chunked with '{stored}' but the code uses '{CHUNKER}'. Mixing them makes chunks "
                "uneven. Re-chunk it with `python scripts/reindex.py --rebuild` (no PDF conversion needed).")
        if not stored and not self.db.execute("SELECT 1 FROM chunks LIMIT 1").fetchone():
            self._set_meta("chunker", CHUNKER)
            self.db.commit()

    def _embed(self, texts: list[str]) -> list:
        """Embed in batches of EMBED_BATCH with a few retries (a request holding hundreds of chunks failed in Ollama)."""
        out: list = []
        for i in range(0, len(texts), EMBED_BATCH):
            batch = texts[i:i + EMBED_BATCH]
            for attempt in range(3):
                try:
                    out += self.embeddings.embed_documents(batch)
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    time.sleep(2 * (attempt + 1))
        return out

    def _check_dim(self, vectors: list) -> None:
        dim = len(vectors[0])
        stored = self._meta("embedding_dim")
        if stored and int(stored) != dim:
            raise EmbeddingMismatch(
                f"The embedding model now in use produces {dim}-number vectors but this library holds "
                f"{stored}-number vectors. Re-embed it with `python scripts/reindex.py --rebuild`.")

    # -- ingestion --

    def ingest_text(self, path: str, markdown: str, title: str = "", source_url: str = "",
                    digest: str | None = None, force: bool = False, status: str = "ok", error: str = "") -> int:
        """Index already-converted markdown under a stable ``path`` key.

        ``digest`` overrides the change-detection key (ingest_file passes the source file's hash so
        unchanged files skip conversion entirely). Everything that can fail (chunking, embedding) happens
        BEFORE anything is written, and the swap of old for new is one transaction, so a failed embed never
        costs you the previous version of the document. A document with no usable text is recorded (status
        'empty') so it is not converted again on every run. Returns the number of chunks (0 if unchanged)."""
        digest = digest or hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        front, body = split_front_matter(markdown)
        kind, front_url = classify_source(path, front)
        source_url = source_url or front_url
        title = title or str(front.get("title") or "")
        with self._lock:
            row = self.db.execute("SELECT id, hash FROM docs WHERE path=?", (path,)).fetchone()
            if row and row[1] == digest and not force:
                return 0
            chunks = chunk_markdown(body) if status == "ok" else []
            vectors = self._embed([c["text"] for c in chunks]) if chunks else []
            if vectors:
                self._check_dim(vectors)
            with self.db:                                  # one transaction: commit, or roll back untouched
                if row:
                    self._delete_doc(row[0])
                doc_status = status if status != "ok" or chunks else "empty"
                cur = self.db.execute(
                    "INSERT INTO docs(path, hash, title, source_url, ingested_at, n_chunks, status, error, markdown, source_kind) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (path, digest, title or Path(path).stem, source_url, datetime.now(UTC).isoformat(),
                     len(chunks), doc_status, error, markdown, kind))
                doc_id = cur.lastrowid
                self._insert_chunks(doc_id, chunks, vectors)
                if vectors and not self._meta("embedding_dim"):
                    self._set_meta("embedding_dim", str(len(vectors[0])))
                self._bump_generation()
            return len(chunks)

    def _insert_chunks(self, doc_id: int, chunks: list[dict], vectors: list) -> None:
        for ord_, (c, v) in enumerate(zip(chunks, vectors, strict=True)):
            cc = self.db.execute(
                "INSERT INTO chunks(doc_id, ord, heading, page, kind, text, embedding) VALUES (?,?,?,?,?,?,?)",
                (doc_id, ord_, c["heading"], c["page"], c["kind"], c["text"], _pack(v)),
            )
            self.db.execute("INSERT INTO chunks_fts(rowid, text, heading) VALUES (?,?,?)",
                            (cc.lastrowid, c["text"], c["heading"]))

    def is_current(self, key: str, digest: str) -> bool:
        row = self.db.execute("SELECT hash FROM docs WHERE path=?", (key,)).fetchone()
        return bool(row and row[0] == digest)

    def ingest_file(self, file: Path, root: Path | None = None, md_out: Path | None = None,
                    namespace: str = "", force: bool = False) -> str:
        """Convert + index one file. Returns "added", "unchanged", "empty" (no usable text), or
        "failed-before" (conversion failed on these exact bytes earlier; retried only if the file changes).

        Unchanged files (same bytes) are skipped BEFORE conversion - Docling is by far the slowest step. A
        conversion failure is recorded against the file's hash so a broken or scanned PDF is not re-converted
        (up to a minute each) at the start of every run. An EMBEDDING failure is not recorded: it is
        transient (Ollama down) and raises so the file is retried next time."""
        rel = file.relative_to(root) if root else Path(file.name)
        key = f"{namespace}/{rel.as_posix()}" if namespace else rel.as_posix()
        digest = "f:" + hashlib.sha256(file.read_bytes()).hexdigest()
        with self._lock:
            row = self.db.execute("SELECT hash, status FROM docs WHERE path=?", (key,)).fetchone()
        if row and row[0] == digest and not force:
            return {"ok": "unchanged", "empty": "empty", "failed": "failed-before"}.get(row[1] or "ok", "unchanged")
        try:
            md = convert_to_markdown(file)
        except Exception as e:
            self.ingest_text(key, "", title=file.stem, digest=digest, status="failed", error=str(e)[:300])
            raise
        if md_out:
            target = (md_out / rel).with_suffix(".md")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(md, encoding="utf-8")
        front, body = split_front_matter(md)
        title = str(front.get("title") or "") or title_from_markdown(body, file.stem)
        n = self.ingest_text(key, md, title=title, digest=digest, force=force)
        return "added" if n else "empty"

    def ingest_folder(self, root: str | Path, md_out: Path | None = None,
                      namespace: str | None = None, force: bool = False) -> dict:
        """Ingest every supported file under root; drop docs whose file is gone.

        Each folder is its own ``namespace`` (default: the folder's name), keys are
        ``<namespace>/<relative path>`` and pruning only touches that namespace - so ingesting a second
        folder never deletes the first folder's documents. (Two folders with the same name need different
        namespaces: pass one explicitly.) ``md_out`` must be OUTSIDE ``root``, or the converted copies would
        be indexed as documents too.
        Returns {"added": n, "unchanged": n, "empty": n, "removed": n, "failed": [..]}."""
        root = Path(root)
        namespace = namespace or root.name
        if md_out is not None and Path(md_out).resolve().is_relative_to(root.resolve()):
            raise ValueError(f"md_out ({md_out}) is inside the folder being indexed ({root}); the converted copies "
                             "would be indexed as separate documents. Choose a folder outside it.")
        stats = {"added": 0, "unchanged": 0, "empty": 0, "removed": 0, "failed": []}
        seen = set()
        for f in sorted(root.rglob("*")):
            if not f.is_file() or f.suffix.lower() not in KB_EXTENSIONS:
                continue
            if any(part in SKIP_DIRS for part in f.relative_to(root).parts[:-1]):
                continue
            seen.add(f"{namespace}/{f.relative_to(root).as_posix()}")
            try:
                outcome = self.ingest_file(f, root, md_out, namespace, force=force)
            except Exception as e:  # one bad PDF must not kill the batch
                stats["failed"].append(f"{f.name}: {e}")
                continue
            if outcome == "failed-before":
                with self._lock:
                    err = self.db.execute("SELECT error FROM docs WHERE path=?",
                                          (f"{namespace}/{f.relative_to(root).as_posix()}",)).fetchone()
                stats["failed"].append(f"{f.name}: could not be converted earlier ({(err[0] if err else '')[:100]}); "
                                       "retried only if the file changes")
            else:
                stats[outcome] += 1
        with self._lock:
            with self.db:
                for doc_id, path in self.db.execute("SELECT id, path FROM docs").fetchall():
                    if path.startswith(f"{namespace}/") and path not in seen:
                        self._delete_doc(doc_id)
                        stats["removed"] += 1
                if stats["removed"]:
                    self._bump_generation()
        return stats

    def _delete_doc(self, doc_id: int):
        for (cid, text, heading) in self.db.execute(
            "SELECT id, text, heading FROM chunks WHERE doc_id=?", (doc_id,)
        ).fetchall():
            self.db.execute(
                "INSERT INTO chunks_fts(chunks_fts, rowid, text, heading) VALUES ('delete',?,?,?)",
                (cid, text, heading),
            )
        self.db.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
        self.db.execute("DELETE FROM docs WHERE id=?", (doc_id,))

    def remove(self, path: str) -> bool:
        """Drop one document (and its chunks) from the index. The file itself is not touched here. Returns False
        when no such document is indexed."""
        with self._lock, self.db:
            row = self.db.execute("SELECT id FROM docs WHERE path=?", (path,)).fetchone()
            if not row:
                return False
            self._delete_doc(row[0])
            self._bump_generation()
            return True

    def set_title(self, path: str, title: str) -> None:
        with self._lock, self.db:
            self.db.execute("UPDATE docs SET title=? WHERE path=?", (title, path))

    def stats(self) -> dict:
        with self._lock:
            d, c = self.db.execute("SELECT COUNT(*), COALESCE(SUM(n_chunks),0) FROM docs WHERE status='ok'").fetchone()
            bad = self.db.execute("SELECT COUNT(*) FROM docs WHERE status != 'ok'").fetchone()[0]
        return {"documents": d, "chunks": c, "unreadable": bad}

    def rebuild(self, embedding_model: str = "") -> dict:
        """Re-chunk and re-embed every document from its saved markdown, with the embeddings currently
        attached (use after changing the embedding model or the chunker). All the embedding is done first;
        the swap is one transaction, so a failure leaves the library as it was. Documents stored before
        markdown was kept cannot be rebuilt: they are listed and left untouched (re-ingest those files)."""
        with self._lock:
            docs = self.db.execute("SELECT id, path, markdown FROM docs WHERE status='ok'").fetchall()
            staged, missing = [], []
            for doc_id, path, md in docs:
                if md is None:
                    missing.append(path)
                    continue
                front, body = split_front_matter(md)
                chunks = chunk_markdown(body)
                vectors = self._embed([c["text"] for c in chunks]) if chunks else []
                staged.append((doc_id, chunks, vectors, classify_source(path, front)))
            if missing:
                raise EmbeddingMismatch(
                    f"{len(missing)} document(s) have no saved text and cannot be rebuilt (first: {missing[0]}). "
                    "Re-ingest them first with `python scripts/ingest_library.py <folder> --force`, or delete "
                    "the library file and ingest again.")
            with self.db:
                for doc_id, chunks, vectors, (kind, url) in staged:
                    for (cid, text, heading) in self.db.execute(
                            "SELECT id, text, heading FROM chunks WHERE doc_id=?", (doc_id,)).fetchall():
                        self.db.execute("INSERT INTO chunks_fts(chunks_fts, rowid, text, heading) VALUES ('delete',?,?,?)",
                                        (cid, text, heading))
                    self.db.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
                    self._insert_chunks(doc_id, chunks, vectors)
                    self.db.execute(
                        "UPDATE docs SET n_chunks=?, source_kind=?, "
                        "source_url=CASE WHEN source_url IS NULL OR source_url='' THEN ? ELSE source_url END WHERE id=?",
                        (len(chunks), kind, url, doc_id))
                dims = {len(v[0]) for _, _, v, _ in staged if v}
                if dims:
                    self._set_meta("embedding_dim", str(dims.pop()))
                if embedding_model:
                    self._set_meta("embedding_model", embedding_model)
                self._set_meta("chunker", CHUNKER)
                self._bump_generation()
            return {"rebuilt": len(staged), "missing_markdown": missing}

    # -- retrieval --

    def _matrix(self):
        """Normalised vector matrix, rebuilt whenever any connection has written since it was cached."""
        generation = self._meta("generation")
        if self._matrix_cache is None or self._matrix_cache[2] != generation:
            rows = self.db.execute("SELECT id, embedding FROM chunks").fetchall()
            if not rows:
                self._matrix_cache = ([], np.zeros((0, 1), dtype=np.float32), generation)
            else:
                ids = [r[0] for r in rows]
                m = np.stack([_unpack(r[1]) for r in rows])
                m = m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-9)
                self._matrix_cache = (ids, m, generation)
        return self._matrix_cache

    def _vector_rank(self, query: str, n: int) -> list[int]:
        ids, m, _ = self._matrix()
        if not ids:
            return []
        q = np.asarray(self.embeddings.embed_query(query), dtype=np.float32)
        if q.shape[0] != m.shape[1]:
            raise EmbeddingMismatch(
                f"The query embedding has {q.shape[0]} numbers but the library's vectors have {m.shape[1]}: the "
                "embedding model has changed. Re-embed with `python scripts/reindex.py --rebuild`.")
        q = q / max(np.linalg.norm(q), 1e-9)
        order = np.argsort(-(m @ q))[:n]
        return [ids[i] for i in order]

    def _keyword_rank(self, query: str, n: int) -> list[int]:
        q = _fts_query(query)
        if not q:
            return []
        rows = self.db.execute(
            "SELECT rowid FROM chunks_fts WHERE chunks_fts MATCH ? ORDER BY bm25(chunks_fts) LIMIT ?",
            (q, n),
        ).fetchall()
        return [r[0] for r in rows]

    def search(self, query: str, k: int = 6, pool: int = 30, skip=None) -> list[dict]:
        """Hybrid search. Returns [{score, text, heading, page, kind, title, path, source_url, source_kind, chunk_id,
        vector_rank, keyword_rank}] (ranks are 1-based, None when that search did not find the chunk; they are kept so
        a run's trace shows why a chunk was picked). ``skip(path, source_kind) -> bool`` leaves a document out."""
        if skip:
            pool *= 3                           # leave room: some of the best matches will be filtered out
        with self._lock:
            fused: dict[int, float] = {}
            ranks: dict[str, dict[int, int]] = {"vector_rank": {}, "keyword_rank": {}}
            for name, ranking in (("vector_rank", self._vector_rank(query, pool)),
                                  ("keyword_rank", self._keyword_rank(query, pool))):
                for rank, cid in enumerate(ranking):
                    fused[cid] = fused.get(cid, 0.0) + 1.0 / (60 + rank)  # RRF
                    ranks[name][cid] = rank + 1
            out = []
            for cid, score in sorted(fused.items(), key=lambda kv: -kv[1]):
                if len(out) >= k:
                    break
                row = self.db.execute(
                    "SELECT c.text, c.heading, c.page, c.kind, d.title, d.path, d.source_url, d.source_kind "
                    "FROM chunks c JOIN docs d ON d.id=c.doc_id WHERE c.id=?",
                    (cid,),
                ).fetchone()
                if row is None:                 # deleted by another connection since the matrix was cached
                    continue
                text, heading, page, kind, title, path, url, source_kind = row
                if skip and skip(path, source_kind or ""):
                    continue
                out.append({"score": score, "text": text, "heading": heading, "page": page,
                            "kind": kind, "title": title, "path": path, "source_url": url or "",
                            "source_kind": source_kind or "", "chunk_id": cid,
                            "vector_rank": ranks["vector_rank"].get(cid), "keyword_rank": ranks["keyword_rank"].get(cid)})
            return out
