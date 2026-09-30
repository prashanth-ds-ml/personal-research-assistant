"""Ingest folders of documents into the persistent knowledge base.

  python scripts/ingest_library.py <folder> [<folder> ...] [--kb path] [--md-out dir] [--force]

The knowledge base location defaults to the same place the deep_research graph
reads from (KB_PATH, else <VAULT_PATH>/.kb/library.sqlite, from .env), and it is opened with the same
embedding model, so the two can never disagree. Each folder is its own namespace (its folder name; two
folders with the same name get a short hash added): re-running on one folder only adds/updates/removes
that folder's documents.

Docling converts PDFs to markdown (tables preserved; OCR off unless a PDF turns out to be scanned). Files
that cannot be converted, or hold no text, are recorded and not retried until they change. --md-out
also writes every converted document as markdown (same folder structure) so it is browsable/editable;
it must be a folder OUTSIDE the ones being indexed. --force re-converts and re-indexes everything.
"""
import argparse
import time
from pathlib import Path

from _common import open_kb

from research_assistant import knowledge


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folders", nargs="+")
    ap.add_argument("--kb", default=None, help="default: KB_PATH or <VAULT_PATH>/.kb/library.sqlite")
    ap.add_argument("--md-out", default="", help="write converted markdown here (one subfolder per input folder)")
    ap.add_argument("--force", action="store_true", help="re-convert and re-index even unchanged files")
    a = ap.parse_args()

    folders = [Path(f) for f in a.folders]
    missing = [str(f) for f in folders if not f.is_dir()]
    if missing:
        ap.error(f"not a folder: {', '.join(missing)}")
    namespaces = knowledge.folder_namespaces(folders)

    with open_kb(a.kb) as kb:
        print("knowledge base:", kb.db_path)
        for folder in folders:
            ns = namespaces[folder.resolve()]
            t = time.time()
            md_out = Path(a.md_out) / ns if a.md_out else None
            stats = kb.ingest_folder(folder, md_out, namespace=ns, force=a.force)
            print(f"{ns}: {stats} in {time.time() - t:.0f}s", flush=True)
        print(kb.stats())


if __name__ == "__main__":
    main()
