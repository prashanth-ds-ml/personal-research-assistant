"""Internal-document retriever: the "search" backend for the customer story
"dig through our scattered internal docs (not the web) and give me a cited
summary".

Loads PDF / Markdown / text files from a folder, chunks them, embeds them and
returns the top-k chunks in the same shape the web-search tools return, so the
rest of the pipeline (summarize, reflect, archive, cite) is untouched.

Citations use a ``doc://<filename>/p<page>-c<chunk>`` URL so the final report's
Sources section points at a file and a page rather than a web address.
"""

import threading
from pathlib import Path
from urllib.parse import quote

DOC_EXTENSIONS = (".pdf", ".md", ".markdown", ".txt")

# (resolved dir, embedding model, newest mtime, file count) -> vector store.
# Research loops call the retriever several times per run; embedding the whole
# corpus each time would dominate latency.
_STORE_CACHE: dict[tuple, object] = {}
_STORE_LOCK = threading.Lock()


def _pdf_pages(path: Path) -> list[tuple[int, str]]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return [(i, page.extract_text() or "") for i, page in enumerate(reader.pages, start=1)]


def load_documents(docs_path: str) -> list[tuple[str, int, str]]:
    """Return (filename, page, text) for every supported file under docs_path.
    Non-PDF files are a single "page" 1. Unreadable files are skipped."""
    root = Path(docs_path)
    if not docs_path or not root.is_dir():
        return []

    out = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in DOC_EXTENSIONS:
            continue
        rel = path.relative_to(root).as_posix()
        try:
            if path.suffix.lower() == ".pdf":
                pages = _pdf_pages(path)
            else:
                pages = [(1, path.read_text(encoding="utf-8", errors="replace"))]
        except Exception as e:
            print(f"Warning: could not read {path}: {e}")
            continue
        out.extend((rel, n, text) for n, text in pages if text.strip())
    return out


def make_embeddings(embedding_model: str, ollama_base_url: str = ""):
    """init_embeddings() with the configured Ollama URL. OllamaEmbeddings
    otherwise ignores OLLAMA_BASE_URL and dials localhost, which is wrong
    inside a container."""
    from langchain.embeddings import init_embeddings

    kwargs = {"base_url": ollama_base_url} if ollama_base_url and embedding_model.startswith("ollama:") else {}
    return init_embeddings(embedding_model, **kwargs)


def _build_store(
    docs_path: str, embedding_model: str, chunk_size: int, embeddings=None, ollama_base_url: str = ""
):
    from langchain_core.documents import Document
    from langchain_core.vectorstores import InMemoryVectorStore
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_size // 10)
    docs = []
    for name, page, text in load_documents(docs_path):
        for c, chunk in enumerate(splitter.split_text(text), start=1):
            docs.append(Document(page_content=chunk, metadata={"file": name, "page": page, "chunk": c}))
    if not docs:
        return None

    if embeddings is None:
        embeddings = make_embeddings(embedding_model, ollama_base_url)
    return InMemoryVectorStore.from_documents(docs, embeddings)


def _fingerprint(docs_path: str) -> tuple:
    files = [
        p for p in Path(docs_path).rglob("*")
        if p.is_file() and p.suffix.lower() in DOC_EXTENSIONS
    ]
    return (len(files), max((p.stat().st_mtime for p in files), default=0.0), sum(p.stat().st_size for p in files))


def local_docs_search(
    query: str,
    docs_path: str,
    embedding_model: str,
    top_k: int = 4,
    chunk_size: int = 1500,
    embeddings=None,
    ollama_base_url: str = "",
) -> dict:
    """Retrieve the top_k chunks for query, shaped like a web-search response:
    {"results": [{title, url, content, raw_content}]}. Empty results if the
    folder is missing/empty (the pipeline then reports no sources)."""
    if not docs_path or not Path(docs_path).is_dir():
        print(f"Warning: docs_path {docs_path!r} is not a directory")
        return {"results": []}

    key = (str(Path(docs_path).resolve()), embedding_model, chunk_size, *_fingerprint(docs_path))
    with _STORE_LOCK:        # comparison mode searches from several threads: build the index once, not once per thread
        if embeddings is not None or key not in _STORE_CACHE:
            store = _build_store(docs_path, embedding_model, chunk_size, embeddings, ollama_base_url)
            if embeddings is None:
                _STORE_CACHE.clear()
                _STORE_CACHE[key] = store
        else:
            store = _STORE_CACHE[key]
    if store is None:
        return {"results": []}

    results = []
    for hit in store.similarity_search(query, k=top_k):
        m = hit.metadata
        text = hit.page_content.strip()
        results.append({
            "title": f"{m['file']} (page {m['page']})",
            "url": f"doc://{quote(m['file'])}/p{m['page']}-c{m['chunk']}",
            "content": text[:500],
            "raw_content": text,
        })
    return {"results": results}
