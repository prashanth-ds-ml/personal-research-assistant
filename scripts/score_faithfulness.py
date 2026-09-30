"""Score the LLM faithfulness judge against human labels.

  python scripts/score_faithfulness.py evals/faithfulness_sheet.csv

`human` column: y = the passage fully supports the claim, n = it does not.
Reports how often the judge agrees with you and, more usefully, its two error
types: it ACCEPTED an unsupported claim (a hallucination gets into the report)
vs it REJECTED a good claim (evidence is wasted).
"""
import csv
import sys


def score(rows: list[dict], column: str = "human") -> dict:
    rows = [{**r, "human": r.get(column, "")} for r in rows]
    labeled = [r for r in rows if r["human"].strip().lower() in ("y", "n")]
    tp = sum(r["judge"] == "y" and r["human"].lower() == "y" for r in labeled)
    tn = sum(r["judge"] == "n" and r["human"].lower() == "n" for r in labeled)
    fp = sum(r["judge"] == "y" and r["human"].lower() == "n" for r in labeled)  # bad claim let through
    fn = sum(r["judge"] == "n" and r["human"].lower() == "y" for r in labeled)  # good claim thrown away
    n = len(labeled)
    div = lambda a, b: a / b if b else float("nan")  # noqa: E731
    return {
        "labeled": n, "accuracy": div(tp + tn, n),
        "precision_of_accepted": div(tp, tp + fp),   # of claims kept, how many are truly supported
        "recall_of_supported": div(tp, tp + fn),     # of truly supported claims, how many are kept
        "false_accepts": fp, "false_rejects": fn,
        "human_supported_rate_among_extracted": div(tp + fn, n),
    }


if __name__ == "__main__":
    path = sys.argv[1]
    column = sys.argv[2] if len(sys.argv) > 2 else "human"   # "claude" = preliminary, AI-labelled
    with open(path, encoding="utf-8-sig") as fh:
        res = score(list(csv.DictReader(fh)), column)
    print(f"labels from column: {column}")
    for k, v in res.items():
        print(f"{k:42s} {v:.1%}" if isinstance(v, float) else f"{k:42s} {v}")
