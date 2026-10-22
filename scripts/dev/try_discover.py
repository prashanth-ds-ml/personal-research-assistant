"""Try the collector's discovery for one question against the REAL services (web search, arXiv, Europe PMC, Hugging Face), without
the model: every result is scored 3, so you see exactly what each source returns. Downloads nothing.

  python scripts/dev/try_discover.py "How do small models handle tool calling?" [--no-hf] [--no-sites]
"""
import argparse
import collections
import json
import sys
import tempfile
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))  # shared helpers: scripts/_common.py

from _common import ROOT  # noqa: F401  (puts src/ on the path)

from research_assistant import collector, fetcher
from research_assistant.configuration import Configuration


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--no-hf", action="store_true")
    ap.add_argument("--no-sites", action="store_true")
    a = ap.parse_args()
    cfg = Configuration()
    judge = lambda prompt, json_mode=False: json.dumps({"score": 3, "query": a.question[:60]})  # noqa: E731
    with tempfile.TemporaryDirectory() as tmp, httpx.Client() as http:
        fx = fetcher.Fetcher(http=http, contact=cfg.contact_email)
        store = fetcher.SourceStore(Path(tmp), "try")
        found = collector.discover(
            [a.question], search=collector.ddgs_search, fx=fx, store=store, llm=judge, per_question=8,
            huggingface=not a.no_hf, extra_sites=None if a.no_sites else collector.split_domains(cfg.collect_extra_sites),
            max_candidates=100_000, on_progress=print)
    by = collections.Counter((d["source"], d["site"] if d["source"] == "web" else "") for d in found)
    print(f"\n{len(found)} candidates")
    for (source, site), n in sorted(by.items(), key=lambda kv: -kv[1]):
        print(f"  {n:3} {source} {site}")
    print()
    for d in found:
        print(f"[{d['kind']:5}] {d['source']:11} {d['site'][:26]:26} {d['title'][:70]}")


if __name__ == "__main__":
    main()
