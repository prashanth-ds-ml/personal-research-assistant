"""Rebuild the knowledge base after a change that affects how documents are stored.

  python scripts/reindex.py --refresh <folder> [<folder> ...]   re-convert and re-index these folders
  python scripts/reindex.py --rebuild                            re-embed everything from the saved text

--refresh: use after upgrading the chunker (for example big tables are now split by rows). It converts every
file again (PDFs take about 20 s each) and stores the converted text inside the library.

--rebuild: use after changing EMBEDDING_MODEL. It needs no source files: the converted text of every document
is stored in the library, so it only re-chunks and re-embeds (minutes, no PDF conversion). The new model and
vector size are recorded; until you do this, the library refuses to open with a different model.
Documents ingested before the text was stored cannot be rebuilt: run --refresh on their folders first.
"""
import argparse
import time
from pathlib import Path

from _common import EMBEDDING_MODEL, open_kb

from research_assistant import knowledge


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default=None)
    ap.add_argument("--refresh", nargs="+", metavar="FOLDER")
    ap.add_argument("--rebuild", action="store_true")
    a = ap.parse_args()
    if not a.refresh and not a.rebuild:
        ap.error("choose --refresh FOLDER... and/or --rebuild")

    if a.refresh:
        folders = [Path(f) for f in a.refresh]
        namespaces = knowledge.folder_namespaces(folders)
        with open_kb(a.kb) as kb:
            for folder in folders:
                t = time.time()
                ns = namespaces[folder.resolve()]
                print(f"{ns}: {kb.ingest_folder(folder, namespace=ns, force=True)} in {time.time() - t:.0f}s", flush=True)
            print(kb.stats())
    if a.rebuild:
        t = time.time()
        with open_kb(a.kb, check_model=False) as kb:          # the point is to change the recorded model
            print(f"re-embedding with {EMBEDDING_MODEL} ...", flush=True)
            print(kb.rebuild(embedding_model=EMBEDDING_MODEL), f"in {time.time() - t:.0f}s")
            print(kb.stats())


if __name__ == "__main__":
    main()
