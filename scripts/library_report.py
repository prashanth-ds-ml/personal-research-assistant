"""What is in the library: documents by folder and kind, and the ones that probably should not be evidence.

  python scripts/library_report.py [--kb path]

Read-only. Deep research leaves out archived copies of your own documents (kind "document" under `Sources/`) unless
you tick "Include archived pages"; real archived web pages stay in. This script shows how much of each there is.
Delete or move files yourself if you want them gone, then the next run's auto-ingest removes them from the index.
"""
import argparse
import collections

from _common import open_kb


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default=None)
    a = ap.parse_args()
    with open_kb(a.kb, check_model=False) as kb:
        rows = kb.db.execute("SELECT path, title, source_kind, n_chunks, status FROM docs ORDER BY path").fetchall()
    by_folder = collections.defaultdict(collections.Counter)
    for path, _title, kind, _n, _status in rows:
        by_folder[path.split("/")[0]][kind or "unknown"] += 1
    print(f"{len(rows)} documents")
    for folder, counts in sorted(by_folder.items()):
        print(f"  {folder:12} " + ", ".join(f"{n} {k}" for k, n in counts.most_common()))
    junk = [(p, t) for p, t, k, n, s in rows if p.startswith("Sources/") and (k in ("document", "") or s != "ok")]
    print(f"\n{len(junk)} archived copies of local documents (left out of deep research by default):")
    for p, t in junk[:40]:
        print(f"  {p}  |  {t[:60]}")
    if len(junk) > 40:
        print(f"  ... and {len(junk) - 40} more")


if __name__ == "__main__":
    main()
