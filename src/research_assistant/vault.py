"""Obsidian vault I/O: source archiving, report writing, profile read/update,
and vault-as-context retrieval for the personal research assistant.
"""

import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import frontmatter

BINARY_URL_EXTENSIONS = (
    ".pdf", ".zip", ".docx", ".xlsx", ".pptx", ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mp3"
)

PROFILE_BOOTSTRAP_TEMPLATE = """---
title: "Research Assistant Profile"
---
## Standing Preferences

*(Edit this section yourself — the assistant never touches it. Add anything you want every research run to account for: depth level, tone, topics to avoid, etc.)*

## Session Log

*(The assistant appends a dated entry here after each research run. Do not hand-edit; prune old entries in Obsidian if it drifts.)*
"""


def slugify(text: str, max_len: int = 60) -> str:
    """Turn arbitrary text into a filesystem/URL-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].strip("-") or "untitled"


def _host_slug(url: str) -> str:
    host = urlparse(url).netloc.removeprefix("www.")
    return slugify(host, max_len=40)


def _looks_binary(url: str, raw_content: str | None) -> bool:
    if urlparse(url).path.lower().endswith(BINARY_URL_EXTENSIONS):
        return True
    if not raw_content:
        return False
    # A crude but cheap corruption check: lots of the unicode replacement
    # character means we likely markdownified decoded binary bytes.
    sample = raw_content[:2000]
    return sample.count("�") > 5


def archive_sources(
    vault_path: str,
    sources_subdir: str,
    topic_slug: str,
    run_date: str,
    search_query: str,
    search_api: str,
    search_results: dict,
) -> list[dict]:
    """Write one markdown file per unique source to
    <vault_path>/<sources_subdir>/<run_date>-<topic_slug>/NN-<host-slug>.md

    Returns a list of archived_sources dicts (index, url, title, query, file_path, fetched_at).
    """
    if not vault_path:
        return []

    run_dir = Path(vault_path) / sources_subdir / f"{run_date}-{topic_slug}"
    run_dir.mkdir(parents=True, exist_ok=True)

    existing = len(list(run_dir.glob("*.md")))
    fetched_at = datetime.now(UTC).isoformat()
    archived = []

    for i, source in enumerate(search_results.get("results", []), start=1):
        url = source.get("url", "")
        title = source.get("title", url)
        raw_content = source.get("raw_content")

        index = existing + i
        file_path = run_dir / f"{index:02d}-{_host_slug(url)}.md"

        if _looks_binary(url, raw_content):
            body = (
                f"*Binary or non-HTML source — full content not archived.*\n\n"
                f"Snippet: {source.get('content', '')}"
            )
        else:
            body = raw_content or source.get("content", "")

        post = frontmatter.Post(
            body,
            title=title,
            url=url,
            query=search_query,
            search_api=search_api,
            fetched_at=fetched_at,
        )
        file_path.write_text(frontmatter.dumps(post), encoding="utf-8")

        archived.append({
            "index": index,
            "url": url,
            "title": title,
            "query": search_query,
            "file_path": str(file_path),
            "fetched_at": fetched_at,
        })

    return archived


def write_report(
    vault_path: str,
    research_subdir: str,
    sources_subdir: str,
    run_date: str,
    topic_slug: str,
    research_topic: str,
    report_body: str,
    archived_sources: list[dict],
    loops: int,
    fallback_sources_text: str | None = None,
) -> str:
    """Assemble frontmatter + report body + a deterministically-built Sources
    section, and write it to <vault_path>/<research_subdir>/<run_date>-<topic_slug>.md
    (or -2/-3/... if that filename is already taken). Returns the file path written.

    If archived_sources is empty (e.g. archive_full_sources was disabled),
    falls back to fallback_sources_text (a plain "* title : url" bullet list)
    instead of the file-linked Sources section.
    """
    research_dir = Path(vault_path) / research_subdir
    research_dir.mkdir(parents=True, exist_ok=True)

    base_name = f"{run_date}-{topic_slug}"
    file_path = research_dir / f"{base_name}.md"
    n = 2
    while file_path.exists():
        file_path = research_dir / f"{base_name}-{n}.md"
        n += 1

    # Later research loops often re-retrieve the same source (esp. with
    # local_docs, where the corpus is small); cite each URL once.
    seen_urls: set[str] = set()
    unique_sources = []
    for src in archived_sources:
        if src["url"] not in seen_urls:
            seen_urls.add(src["url"])
            unique_sources.append(src)

    sources_lines = []
    for display_index, src in enumerate(unique_sources, start=1):
        rel = Path(src["file_path"]).relative_to(Path(vault_path) / sources_subdir)
        sources_lines.append(f"{display_index}. [{src['title']}](../{sources_subdir}/{rel.as_posix()}) — {src['url']}")
    if sources_lines:
        sources_section = "\n".join(sources_lines)
    elif fallback_sources_text:
        sources_section = fallback_sources_text
    else:
        sources_section = "*No sources archived this run.*"

    full_body = f"{report_body.strip()}\n\n## Sources\n{sources_section}\n"

    post = frontmatter.Post(
        full_body,
        title=research_topic,
        date=run_date,
        topic_slug=topic_slug,
        loops=loops,
        sources_count=len(unique_sources),
        status="complete",
    )
    file_path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return str(file_path)


def read_profile(vault_path: str, profile_note_path: str) -> str:
    """Return the profile note's raw text, creating it from the bootstrap
    template if the vault or file doesn't exist yet."""
    if not vault_path:
        return PROFILE_BOOTSTRAP_TEMPLATE

    path = Path(vault_path) / profile_note_path
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(PROFILE_BOOTSTRAP_TEMPLATE, encoding="utf-8")
        return PROFILE_BOOTSTRAP_TEMPLATE

    return path.read_text(encoding="utf-8")


def append_profile_session(
    vault_path: str,
    profile_note_path: str,
    run_date: str,
    research_topic: str,
    session_bullets: str,
) -> None:
    """Append a new dated Session Log subsection to the profile note.
    Additive only — never rewrites existing content, including
    "## Standing Preferences", which stays human-owned.
    """
    if not vault_path:
        return

    path = Path(vault_path) / profile_note_path
    text = path.read_text(encoding="utf-8") if path.exists() else PROFILE_BOOTSTRAP_TEMPLATE

    entry = f"\n### {run_date} — {research_topic}\n{session_bullets.strip()}\n"

    marker = "## Session Log"
    idx = text.find(marker)
    if idx == -1:
        # Shouldn't happen given the bootstrap template, but don't lose the entry.
        text = text.rstrip() + f"\n\n{marker}\n{entry}"
    else:
        insert_at = idx + len(marker)
        text = text[:insert_at] + entry + text[insert_at:]

    path.write_text(text, encoding="utf-8")


def retrieve_vault_context(
    vault_path: str,
    research_subdir: str,
    embedding_model: str,
    topic: str,
    top_k: int,
    ollama_base_url: str = "",
) -> str:
    """Embed existing Research/ notes and return the top_k most relevant as
    formatted markdown snippets. Returns "" if the vault/folder is empty or
    missing — callers should treat that as "no prior research"."""
    if not vault_path:
        return ""

    research_dir = Path(vault_path) / research_subdir
    notes = sorted(research_dir.glob("*.md")) if research_dir.exists() else []
    if not notes:
        return ""

    from langchain_core.documents import Document
    from langchain_core.vectorstores import InMemoryVectorStore
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=50)
    docs = []
    for note_path in notes:
        post = frontmatter.load(note_path)
        title = post.get("title", note_path.stem)
        for chunk in splitter.split_text(post.content):
            docs.append(Document(page_content=chunk, metadata={"title": title, "path": note_path.name}))

    if not docs:
        return ""

    from research_assistant.documents import make_embeddings

    embeddings = make_embeddings(embedding_model, ollama_base_url)
    store = InMemoryVectorStore.from_documents(docs, embeddings)
    hits = store.similarity_search(topic, k=top_k)

    snippets = []
    for hit in hits:
        snippets.append(
            f"### {hit.metadata['title']} ({hit.metadata['path']})\n{hit.page_content.strip()}"
        )
    return "\n\n".join(snippets)


# ---- report feedback (the dashboard writes the same frontmatter fields) ---------------------

FEEDBACK_RATINGS = ("up", "down")


def set_feedback(vault_path: str, research_subdir: str, slug: str, rating: str, note: str = "") -> Path:
    """Record whether a report was useful in its own frontmatter:
    feedback_rating (up|down), feedback_note, feedback_at."""
    if rating not in FEEDBACK_RATINGS:
        raise ValueError(f"rating must be one of {FEEDBACK_RATINGS}")
    path = Path(vault_path) / research_subdir / f"{slug}.md"
    post = frontmatter.load(path)
    post["feedback_rating"] = rating
    post["feedback_note"] = note.strip()
    post["feedback_at"] = datetime.now(UTC).isoformat()
    path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return path


def recent_feedback(vault_path: str, research_subdir: str, n: int = 5) -> list[dict]:
    """The n most recent reports that have a rating: [{title, goal, rating, note, at}]."""
    folder = Path(vault_path) / research_subdir
    if not vault_path or not folder.is_dir():
        return []
    items = []
    for path in folder.glob("*.md"):
        try:
            post = frontmatter.load(path)
        except Exception:
            continue
        if post.get("feedback_rating") in FEEDBACK_RATINGS:
            items.append({"title": post.get("title", path.stem), "goal": post.get("goal", ""),
                          "rating": post["feedback_rating"], "note": str(post.get("feedback_note", "")),
                          "at": str(post.get("feedback_at", ""))})
    return sorted(items, key=lambda x: x["at"], reverse=True)[:n]
