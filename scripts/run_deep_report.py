"""Thin-slice goal -> long report, from the local knowledge base only.

  python scripts/run_deep_report.py "<goal>" --kb library_kb.sqlite --out report.md \
      [--plan-model qwen3:8b] [--extract-model llama3.1:8b] [--write-model llama3.1:8b] [--top-k 6]
"""
import argparse
import time
from pathlib import Path

from _common import OLLAMA_URL, open_kb  # noqa: E402

from research_assistant import deep_report, knowledge  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("goal")
    ap.add_argument("--kb", default=knowledge.default_kb_path())
    ap.add_argument("--out", default="report.md", help="where to write the markdown report")
    ap.add_argument("--plan-model", default="llama3.1:8b")
    ap.add_argument("--extract-model", default="llama3.1:8b")
    ap.add_argument("--write-model", default="llama3.1:8b")
    ap.add_argument("--top-k", type=int, default=6)
    ap.add_argument("--embedding-model", default=None, help="default: EMBEDDING_MODEL from .env")
    a = ap.parse_args()

    url = OLLAMA_URL
    kb = open_kb(a.kb, a.embedding_model)
    print("KB:", kb.stats())
    t0 = time.time()
    report, stats = deep_report.run(
        a.goal,
        search=lambda q: kb.search(q, k=a.top_k),
        plan_llm=deep_report.ollama_llm(a.plan_model, url, temperature=0),
        extract_llm=deep_report.ollama_llm(a.extract_model, url, temperature=0),
        write_llm=deep_report.ollama_llm(a.write_model, url),
        library_size=kb.stats()["documents"],
        on_progress=lambda s: print(f"[{time.time() - t0:5.0f}s] {s}", flush=True),
    )
    Path(a.out).write_text(report, encoding="utf-8")
    print(stats, f"in {time.time() - t0:.0f}s ->", a.out)


if __name__ == "__main__":
    main()
