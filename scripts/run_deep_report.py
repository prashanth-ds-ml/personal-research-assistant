"""Thin-slice goal -> report, from the local knowledge base only (no clarify / approve / collect steps).

  python scripts/run_deep_report.py "<goal>" --kb library_kb.sqlite --out report.md [--model qwen3.5:4b] [--top-k 6]
                                    [--facts] [--think-plan] [--think-write]

v3 default: one model, sections written from the library passages. ``--facts`` runs the v2 pipeline (extract facts,
then write from them) for comparison. With VAULT_PATH set, the run is traced in <vault>/.desk/desk.sqlite as "cli-<time>"
(one step, "run"; the dashboard graph records each step separately).
"""
import argparse
import os
import time
from datetime import datetime
from pathlib import Path

from _common import OLLAMA_URL, open_kb  # noqa: E402

from research_assistant import deep_report, desk, knowledge, rerank  # noqa: E402
from research_assistant import report_checks as rc  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("goal")
    ap.add_argument("--kb", default=knowledge.default_kb_path())
    ap.add_argument("--out", default="report.md", help="where to write the markdown report")
    ap.add_argument("--model", default="qwen3.5:4b")
    ap.add_argument("--top-k", type=int, default=6)
    ap.add_argument("--facts", action="store_true", help="v2 pipeline: extract facts, write from facts")
    ap.add_argument("--think-plan", action="store_true", help="let the model think before planning (~85 s per call)")
    ap.add_argument("--think-write", action="store_true", help="let the model think before each section (~90 s each)")
    ap.add_argument("--rerank", action="store_true", help="M3: rerank a pool of 24 passages per question, keep the best 8")
    ap.add_argument("--embedding-model", default=None, help="default: EMBEDDING_MODEL from .env")
    a = ap.parse_args()

    url = OLLAMA_URL
    kb = open_kb(a.kb, a.embedding_model)
    print("KB:", kb.stats())
    t0 = time.time()
    trace = desk.RunTrace(os.environ.get("VAULT_PATH", ""), f"cli-{datetime.now():%Y%m%d-%H%M%S}")
    trace.start_run(a.goal, deep_report.engine_version(a.rerank) if not a.facts else "v2-facts", a.model,
                    {"top_k": a.top_k, "think_plan": a.think_plan, "think_write": a.think_write, "facts": a.facts})
    with trace.step("run"):
        report, stats = run(a, kb, url, t0)
    trace.sentences(report)
    trace.finish_run("complete", str(Path(a.out).resolve()), stats)
    Path(a.out).write_text(report, encoding="utf-8")
    print(stats, f"in {time.time() - t0:.0f}s ->", a.out, f"(trace: {trace.run_id})" if trace.enabled else "")


def run(a, kb, url, t0):
    return deep_report.run(
        a.goal,
        search=lambda q: kb.search(q, k=a.top_k),
        plan_llm=deep_report.ollama_llm(a.model, url, temperature=0, reasoning=a.think_plan, role="planner"),
        extract_llm=deep_report.ollama_llm(a.model, url, temperature=0, reasoning=False, role="judge"),
        write_llm=deep_report.ollama_llm(a.model, url, reasoning=a.think_write, role="writer"),
        library_size=kb.stats()["documents"],
        on_progress=lambda s: print(f"[{time.time() - t0:5.0f}s] {s}", flush=True),
        standards=rc.Standards(min_facts=2, flags_only=True) if not a.facts else rc.Standards(),
        passages=not a.facts,
        reranker=rerank.get() if a.rerank else None,
    )


if __name__ == "__main__":
    main()
