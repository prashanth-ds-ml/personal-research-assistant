"""Does a run survive the browser disconnecting (clicking away from the page)?

Starts an autonomous deep-research run (the dashboard stream sends on_disconnect=cancel by default), closes the connection after the first event (what a page
navigation does to the dashboard's stream), waits, and reports the run's status. Run it with the
default behaviour and with on_disconnect=continue; cancels the run afterwards so it does not burn
the GPU.

  python scripts/check_disconnect.py [--api http://localhost:2025]
"""
import argparse
import json
import time

import httpx


def trial(api: str, on_disconnect: str | None, wait: float) -> str:
    c = httpx.Client(base_url=api, timeout=60)
    thread = c.post("/threads", json={}).json()["thread_id"]
    body = {"assistant_id": "deep_research", "input": {"goal": "What is hybrid retrieval and when does it help?"},
            "config": {"configurable": {"ask_clarifying_questions": False, "require_plan_approval": False,
                                        "auto_ingest": False}},
            "stream_mode": ["values"], "stream_resumable": True}
    if on_disconnect:
        body["on_disconnect"] = on_disconnect
    with c.stream("POST", f"/threads/{thread}/runs/stream", json=body) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line.startswith("data:"):
                break                                   # got the first event; now "navigate away"
    time.sleep(wait)
    runs = c.get(f"/threads/{thread}/runs").json()
    status = runs[0]["status"] if runs else "no run"
    for run in runs:                                    # tidy up: never leave a long run going
        if run["status"] in ("running", "pending"):
            c.post(f"/threads/{thread}/runs/{run['run_id']}/cancel")
    return status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:2025")
    ap.add_argument("--wait", type=float, default=20)
    a = ap.parse_args()
    for mode in ("cancel", "continue"):
        status = trial(a.api, mode, a.wait)
        print(json.dumps({"on_disconnect": mode or "(default)", f"status_after_{a.wait:.0f}s": status}))


if __name__ == "__main__":
    main()
