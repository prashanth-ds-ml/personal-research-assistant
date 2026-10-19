"""Re-index or remove ONE library document. The dashboard's Library page calls this; it prints one JSON line.

  python scripts/library_doc.py reindex "Library/2026-10-01-some-goal/paper.md"
  python scripts/library_doc.py remove  "Library/2026-10-01-some-goal/paper.md"

The key is the document's path inside the index: "<folder name>/<path inside that folder>", where the folder is one
of the library folders (<vault>/Sources, <vault>/Library). Anything else is refused, so a crafted key can never reach
outside them.

  reindex  converts and indexes the file again (use it after you edited the file, or if it was unreadable).
  remove   takes it out of the index AND moves the file to <vault>/.removed/<key>, so it stops being searched
           and the next library refresh does not bring it back. Nothing is deleted: move the file back to restore it.
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from _common import open_kb

from research_assistant import knowledge


def _resolve(key: str, vault: Path) -> tuple[Path, Path, str]:
    """(library folder, file, namespace) for an index key, or raise ValueError."""
    folders = [p for p in (vault / "Sources", vault / "Library") if p.is_dir()]
    namespaces = knowledge.folder_namespaces(folders)
    ns, _, rel = key.partition("/")
    for folder in folders:
        if namespaces[folder.resolve()] == ns and rel:
            root = folder.resolve()
            file = (root / rel).resolve()
            if not file.is_relative_to(root):
                raise ValueError("path leaves the library folder")
            return root, file, ns
    raise ValueError(f"not in a library folder: {key}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["reindex", "remove"])
    ap.add_argument("key")
    a = ap.parse_args()
    vault_env = os.environ.get("VAULT_PATH", "")
    if not vault_env:
        print(json.dumps({"ok": False, "error": "VAULT_PATH is not set"}))
        return 1
    vault = Path(vault_env)
    try:
        root, file, ns = _resolve(a.key, vault)
        with open_kb(knowledge.default_kb_path(vault_env)) as kb:
            if a.action == "reindex":
                if not file.is_file():
                    raise ValueError("the file is no longer on disk")
                outcome = kb.ingest_file(file, root, None, ns, force=True)
                print(json.dumps({"ok": True, "outcome": outcome}))
            else:
                removed = kb.remove(a.key)
                moved = ""
                if file.is_file():
                    target = vault / ".removed" / a.key
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if target.exists():
                        target = target.with_name(f"{target.stem}-{int(file.stat().st_mtime)}{target.suffix}")
                    shutil.move(str(file), str(target))
                    moved = str(target)
                print(json.dumps({"ok": True, "removed_from_index": removed, "moved_to": moved}))
    except Exception as e:  # report it to the page instead of a traceback
        print(json.dumps({"ok": False, "error": str(e)[:300]}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
