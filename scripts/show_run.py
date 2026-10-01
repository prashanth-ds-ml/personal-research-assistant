"""Print a deep-research run's live state from the dashboard's API: where it is, progress, last events.

  python scripts/show_run.py            # the newest run
  python scripts/show_run.py <run id prefix> [--events 20] [--api http://localhost:3001/api]
"""
import argparse
import json
import urllib.request


def get(url):
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.load(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run", nargs="?", default="")
    ap.add_argument("--events", type=int, default=12)
    ap.add_argument("--api", default="http://localhost:3001/api")
    a = ap.parse_args()
    runs = get(f"{a.api}/runs")["runs"]
    runs = [r for r in runs if r["id"].startswith(a.run)]
    if not runs:
        print("no matching run")
        return 1
    run = get(f"{a.api}/runs/{runs[0]['id']}")
    print(f"{run['id'][:8]}  {run['status']}  step={run['step']}  waiting_for={run['waitingFor']}")
    print("goal:", run["goal"].splitlines()[0][:100])
    print("progress:", run["progress"])
    if run["note"]:
        print("note:", run["note"])
    for e in run["events"][-a.events:]:
        print(" ", e["t"][11:19], e["text"][:140])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
