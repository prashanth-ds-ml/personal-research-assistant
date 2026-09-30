"""Fetch open-access papers (arXiv, Europe PMC) and pages you name into the library, then index them.

  python scripts/collect.py "How does hybrid retrieval compare with dense-only retrieval?" [--max 5]
  python scripts/collect.py --seed https://example.org/article --seed https://example.org/paper.pdf

Saves to <vault>/Library/<date>-<slug>/ (markdown + provenance frontmatter, original PDFs in raw/,
manifest.json listing every candidate and why it was kept or skipped), then indexes the folder so the
next deep-research run can cite it. Polite by design: arXiv is paced at one request per 3 seconds,
seed URLs obey robots.txt, content stays private.
"""
import argparse
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import httpx  # noqa: E402
from _common import open_kb  # noqa: E402

from research_assistant import deep_report, fetcher, knowledge, vault  # noqa: E402
from research_assistant.goal_graph import _pdf_to_markdown  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("questions", nargs="*", help="research questions to search for")
    ap.add_argument("--seed", action="append", default=[], help="a page or PDF URL to fetch (repeatable)")
    ap.add_argument("--max", type=int, default=5, help="maximum sources to save")
    ap.add_argument("--keep-score", type=int, default=3, help="minimum relevance 0-3 to keep (3 = directly answers)")
    ap.add_argument("--model", default=os.environ.get("LOCAL_LLM", "llama3.1:8b"))
    ap.add_argument("--contact", default=os.environ.get("CONTACT_EMAIL", ""))
    ap.add_argument("--no-index", action="store_true", help="save only; do not index into the knowledge base")
    a = ap.parse_args()
    if not a.questions and not a.seed:
        ap.error("give at least one question or --seed URL")

    vault_path = os.environ.get("VAULT_PATH", "")
    if not vault_path:
        sys.exit("VAULT_PATH is not set (see .env)")
    library = Path(vault_path) / "Library"
    library.mkdir(parents=True, exist_ok=True)
    label = vault.slugify(a.questions[0] if a.questions else a.seed[0], max_len=50)
    store = fetcher.SourceStore(library, f"{date.today().isoformat()}-{label}")
    url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    llm = deep_report.ollama_llm(a.model, url, temperature=0)

    with httpx.Client() as http:
        fx = fetcher.Fetcher(http=http, contact=a.contact)
        summary = fetcher.collect(a.questions, store, fx, llm, seeds=a.seed, max_sources=a.max,
                                  keep_score=a.keep_score, convert_pdf=_pdf_to_markdown,
                                  on_progress=lambda s: print(" ", s, flush=True))
    print("\nResult:", summary)
    for m in store.manifest:
        print(f"  [{m['status']:7s}] rel={m['relevance']:>2} {m['source']:9s} {m['title'][:62]}"
              + (f"  ({m['reason']})" if m["reason"] else ""))
    if summary["saved"] and not a.no_index:
        with open_kb(knowledge.default_kb_path(vault_path)) as kb:
            ns = knowledge.folder_namespaces([library])[library.resolve()]
            print("\nIndexed:", kb.ingest_folder(library, namespace=ns), "| library now:", kb.stats())
    print("Manifest:", Path(summary["folder"]) / "manifest.json")


if __name__ == "__main__":
    main()
