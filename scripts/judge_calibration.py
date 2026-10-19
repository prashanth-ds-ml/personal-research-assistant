"""Judge calibration (P0.2): how often the faithfulness judge agrees with a person.

  python scripts/judge_calibration.py [--sheet evals/faithfulness_sheet.csv] [--human evals/faithfulness_human.csv]
                                      [--column judge]

The decision number is agreement with HUMAN labels only. They come from a blind copy (the user never sees the
judge's or Claude's verdicts), joined by id; a "human" column in the sheet counts too. Rule from the phase doc: the
judge is used for evaluation only if its agreement with the human labels is at least 85%.

Also printed, as an upper bound only: agreement with a mixed reference (human label, else the label the judge and
Claude agree on). For rows nobody labelled that reference is circular, which is why it is not the decision number.
``--column`` scores another labeller column (e.g. a new judge model's output added later).

  python scripts/judge_calibration.py --make-blind 20 [--seed 3]

writes the blind copy: the disputed rows plus random others up to N, shuffled, with id, question, source, claim,
quote, context and an empty "human" column (y = the passage supports the claim, n = it does not).
"""
import argparse
import csv
import random
import sys
from pathlib import Path

from _common import default_paths  # noqa: E402

from research_assistant import eval_tools as et  # noqa: E402

THRESHOLD = 0.85
DISPUTED = ["2", "9", "11", "16", "25", "31", "34", "39"]      # judge and Claude disagree, or flagged borderline
BLIND_FIELDS = ["id", "question", "source", "claim", "quote", "context", "human", "note"]


def make_blind(rows: list[dict], n: int, seed: int, path: Path):
    if path.exists():
        sys.exit(f"{path} exists; it may hold labels. Move it away first.")
    rest = [r["id"] for r in rows if r["id"] not in DISPUTED]
    pick = DISPUTED + random.Random(seed).sample(rest, max(0, n - len(DISPUTED)))
    random.Random(seed + 1).shuffle(pick)                  # disputed rows are not grouped together
    by_id = {r["id"]: r for r in rows}
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=BLIND_FIELDS)
        w.writeheader()
        for i in pick:
            w.writerow({k: by_id[i].get(k, "") for k in BLIND_FIELDS[:6]} | {"human": "", "note": ""})
    print(f"wrote {path}: {len(pick)} rows ({len(DISPUTED)} disputed + {len(pick) - len(DISPUTED)} random, shuffled)")


def report(rows: list[dict], column: str):
    labelled = [r for r in rows if r.get("human", "").strip().lower() in ("y", "n")]
    print(f"human labels: {len(labelled)}")
    for col in dict.fromkeys([column, "claude"]):
        a = et.agreement([(r[col], r["human"]) for r in labelled if r.get(col, "").strip()])
        if a["n"]:
            verdict = "PASS" if a["rate"] >= THRESHOLD else "FAIL"
            print(f"  {col} vs human: {a['agree']}/{a['n']} = {a['rate']:.0%} (kappa {a['kappa']:.2f}) -> {verdict} "
                  f"(threshold {THRESHOLD:.0%}); confusion {a['confusion']}")
    if not labelled:
        print("  (no human labels yet: the decision number cannot be computed)")

    ref = et.reference_labels(rows)
    unsettled = [r["id"] for r in rows if r["id"] not in ref]
    print(f"\nupper bound only (mixed reference, circular where nobody labelled): {len(ref)} rows with a reference")
    if unsettled:
        print("  unsettled: " + ", ".join(unsettled))
    for col in dict.fromkeys([column, "claude"]):
        a = et.agreement([(r[col], ref[r["id"]]) for r in rows if r["id"] in ref and r.get(col, "").strip()])
        if a["n"]:
            print(f"  {col} vs mixed reference: {a['agree']}/{a['n']} = {a['rate']:.0%}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sheet", default=default_paths()["sheet"])
    p.add_argument("--human", default=str(Path(default_paths()["sheet"]).with_name("faithfulness_human.csv")))
    p.add_argument("--column", default="judge")
    p.add_argument("--make-blind", type=int, default=0)
    p.add_argument("--seed", type=int, default=3)
    args = p.parse_args()
    with open(args.sheet, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if args.make_blind:
        return make_blind(rows, args.make_blind, args.seed, Path(args.human))
    if Path(args.human).exists():
        with open(args.human, encoding="utf-8-sig") as f:
            human = {r["id"]: r.get("human", "").strip().lower() for r in csv.DictReader(f)}
        for r in rows:
            if human.get(r["id"]) in ("y", "n"):
                r["human"] = human[r["id"]]
    report(rows, args.column)


if __name__ == "__main__":
    main()
