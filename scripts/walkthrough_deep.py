"""End-to-end check of the Deep Research flow through the dashboard's API proxy,
making the same calls the /deep page makes (LangGraph SDK `useStream`):

  start -> clarify interrupt -> resume(answers) -> plan interrupt
        -> resume({feedback}) -> revised plan interrupt -> resume({approved}) -> report

Real backend, real models, real library. Run it with the services up:

  python scripts/walkthrough_deep.py "<goal>" [--api http://localhost:3001/api]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import httpx


def pretty(label: str, t0: float, text: str = ""):
    print(f"[{time.time() - t0:5.0f}s] {label} {text}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("goal")
    ap.add_argument("--api", default="http://localhost:3001/api")
    ap.add_argument("--feedback", default="add a section on cost and operational effort")
    ap.add_argument("--plan-only", action="store_true", help="stop after the revised plan (fast check of planning)")
    a = ap.parse_args()
    t0 = time.time()
    c = httpx.Client(base_url=a.api, timeout=3600)

    graphs = {x["graph_id"] for x in c.post("/assistants/search", json={"limit": 50}).json()}
    pretty("graphs registered:", t0, str(sorted(graphs)))
    assert "deep_research" in graphs, "deep_research graph is not registered - restart the backend"

    thread = c.post("/threads", json={}).json()["thread_id"]

    def run(payload):
        r = c.post(f"/threads/{thread}/runs/wait", json={"assistant_id": "deep_research", **payload})
        r.raise_for_status()
        return r.json()

    def interrupt_of(out):
        intr = out.get("__interrupt__") if isinstance(out, dict) else None
        return intr[0]["value"] if intr else None

    out = run({"input": {"goal": a.goal}})
    q = interrupt_of(out)
    assert q and q["type"] == "clarify", f"expected clarify interrupt, got {json.dumps(out)[:300]}"
    pretty("PAUSE 1 clarify:", t0, json.dumps(q["questions"]))

    answers = "\n".join(f"{x}\n  -> (walkthrough) not specified, use sensible defaults" for x in q["questions"][:2])
    out = run({"command": {"resume": answers}})
    p1 = interrupt_of(out)
    assert p1 and p1["type"] == "approve_plan", f"expected plan interrupt, got {json.dumps(out)[:300]}"
    pretty("PAUSE 2 plan:", t0, f"{len(p1['plan']['sub_questions'])} questions, sections = "
                                f"{[s['title'] for s in p1['plan']['outline']]}, revisions_left={p1['revisions_left']}")

    out = run({"command": {"resume": {"feedback": a.feedback}}})
    p2 = interrupt_of(out)
    assert p2 and p2["type"] == "approve_plan", f"expected revised plan, got {json.dumps(out)[:300]}"
    pretty("PAUSE 2 revised plan:", t0, f"sections = {[s['title'] for s in p2['plan']['outline']]}, "
                                        f"revisions_left={p2['revisions_left']}")

    titles = [s["title"] for s in p2["plan"]["outline"]]
    assert p2["plan"]["outline"][-1].get("synthesis"), f"revised plan lost its synthesis section: {titles}"
    assert not all(t.endswith("?") for t in titles), f"plan fell back to raw questions as sections: {titles}"
    if a.plan_only:
        pretty("plan-only check passed (thread left paused)", t0)
        return 0
    pretty("approving; extraction + writing starts (takes several minutes)", t0)
    out = run({"command": {"resume": {"approved": True}}})
    assert "__interrupt__" not in out, f"unexpected pause: {json.dumps(out)[:300]}"
    path = out.get("report_path")
    pretty("DONE:", t0, f"stats={out.get('stats')} report={path}")
    assert path and Path(path).exists(), "report file was not written to the vault"
    text = Path(path).read_text(encoding="utf-8")
    sources = text.split("## Sources")[1].split("## Evidence")[0] if "## Sources" in text else ""
    pretty("report sources:", t0, " | ".join(ln[2:70] for ln in sources.splitlines() if ln.startswith("- ")))
    empty = text.count("No supporting evidence")
    pretty(f"sections with no evidence: {empty}; slug for the dashboard:", t0, Path(path).stem)
    return 0


if __name__ == "__main__":
    sys.exit(main())
