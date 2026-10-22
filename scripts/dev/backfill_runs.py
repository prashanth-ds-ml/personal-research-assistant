"""Create run records (see src/research_assistant/runlog.py) for deep-research threads that already exist in the
backend but were started before runs were recorded, so they show up on the dashboard's Runs page.

  python scripts/dev/backfill_runs.py            # dry run: list what would be created
  python scripts/dev/backfill_runs.py --write    # create the records in <vault>/.runs

Threads that already have a record are left alone. A thread the backend still shows as busy whose latest run is no
longer running (a ghost left by a cancelled run) is recorded as stopped.
"""
import argparse
import json
import os
from pathlib import Path

import httpx

from research_assistant import runlog

WAITING = {"clarify": "clarify", "approve_plan": "approve", "review_sources": "review"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--backend", default="http://127.0.0.1:2025")
    ap.add_argument("--vault", default=os.environ.get("VAULT_PATH", ""))
    a = ap.parse_args()
    if not a.vault:
        raise SystemExit("set VAULT_PATH or pass --vault")
    c = httpx.Client(base_url=a.backend, timeout=30)
    made = 0
    for t in c.post("/threads/search", json={"limit": 200}).json():
        tid = t["thread_id"]
        values = t.get("values") or {}
        goal = values.get("goal")
        if not goal or "plan" not in values and t["status"] == "idle" and not values.get("report_path"):
            if not goal:
                continue                               # a quick-research thread, not a deep-research one
        if runlog.read_run(a.vault, tid):
            continue
        interrupts = [i.get("value", {}) for lst in (t.get("interrupts") or {}).values() for i in lst]
        kind = next((WAITING[v["type"]] for v in interrupts if isinstance(v, dict) and v.get("type") in WAITING), None)
        runs = c.get(f"/threads/{tid}/runs").json()
        latest = runs[0]["status"] if runs else ""
        report = values.get("report_path", "")
        if report:
            status = "done"
        elif t["status"] == "interrupted" and kind:
            status = "waiting"
        elif t["status"] == "busy" and latest != "running":
            status = "stopped"
        elif t["status"] == "error":
            status = "failed"
        else:
            status = "stopped"
        plan = values.get("plan") or {}
        print(f"{tid[:8]}  {status:8} {kind or '':8} {goal.splitlines()[0][:70]}")
        if not a.write:
            continue
        log = runlog.RunLog(a.vault, tid)
        log.start(goal)
        log.progress(questions_total=len(plan.get("sub_questions", [])) or None)

        def fill(d, status=status, kind=kind, report=report, t=t, values=values):
            d.update(status=status, waiting_for=kind if status == "waiting" else None, report_path=report,
                     step={"waiting": kind or "", "done": "done"}.get(status, d.get("step", "")),
                     started_at=t.get("created_at", d.get("started_at")), stats=values.get("stats") or {})
            d["events"] = [{"t": t.get("updated_at", ""), "text": "Recorded later from the backend (this run started "
                                                                  "before runs were recorded)"}]

        log._mutate(fill)
        # _mutate stamps updated_at with "now"; restore the thread's own time so the history order is right
        path = Path(a.vault) / runlog.RUNS_DIR / f"{tid}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["updated_at"] = t.get("updated_at", data["updated_at"])
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        made += 1
    print(f"{made} record(s) written" if a.write else "dry run; pass --write to create the records")


if __name__ == "__main__":
    main()
