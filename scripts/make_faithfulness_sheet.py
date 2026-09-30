"""Build a sheet of extracted claims for a HUMAN to label, so the LLM judge can be
scored against ground truth (scripts/score_faithfulness.py).

For each eval question we retrieve passages, extract candidate facts WITHOUT the
judge, then run the judge only to record its verdict. The sheet is sampled to
contain both judge-accepted and judge-rejected claims (otherwise you could not
measure how many good claims the judge wrongly throws away).

  python scripts/make_faithfulness_sheet.py --kb library_kb.sqlite --n 50 --out evals/faithfulness_sheet.csv

Fill the `human` column with y (claim is fully supported by the passage) or n,
then run score_faithfulness.py.
"""
import argparse
import csv
import json
import random
from pathlib import Path

from _common import OLLAMA_URL, default_paths, open_kb  # noqa: E402

from research_assistant import deep_report as d  # noqa: E402
from research_assistant import knowledge  # noqa: E402


def window(text: str, quote: str, pad: int = 350) -> str:
    i = text.lower().find(quote.lower()[:40])
    if i < 0:
        return text[: 2 * pad]
    return text[max(0, i - pad): i + len(quote) + pad].replace("\n", " ")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default=knowledge.default_kb_path())
    ap.add_argument("--qa", default=default_paths()["qa"])
    ap.add_argument("--model", default="llama3.1:8b", help="extractor model (judge uses the same by default)")
    ap.add_argument("--judge-model", default="")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--out", default=default_paths()["sheet"])
    ap.add_argument("--seed", type=int, default=7)
    a = ap.parse_args()

    url = OLLAMA_URL
    kb = open_kb(a.kb)
    extract_llm = d.ollama_llm(a.model, url, temperature=0)
    judge_llm = d.ollama_llm(a.judge_model or a.model, url, temperature=0)

    rows = []
    for r in json.load(open(a.qa, encoding="utf-8")):
        for hit in kb.search(r["q"], k=2):
            for f in d.extract_facts(r["q"], hit, extract_llm, check_entailment=False):
                verdict = d._entailed(f["claim"], f["quote"], hit["text"], judge_llm)
                rows.append({"question": r["q"], "source": hit["title"], "claim": f["claim"],
                             "quote": f["quote"], "context": window(hit["text"], f["quote"]),
                             "judge": "y" if verdict else "n", "human": ""})
        print(f"{len(rows)} candidate claims", flush=True)

    random.Random(a.seed).shuffle(rows)
    yes = [r for r in rows if r["judge"] == "y"]
    no = [r for r in rows if r["judge"] == "n"]
    half = a.n // 2
    sample = yes[:half] + no[: a.n - min(half, len(yes))]
    random.Random(a.seed).shuffle(sample)
    for i, r in enumerate(sample, 1):
        r["id"] = i
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "question", "source", "claim", "quote", "context", "judge", "human"])
        w.writeheader()
        w.writerows(sample)
    print(f"Wrote {len(sample)} claims ({sum(r['judge'] == 'y' for r in sample)} judge-accepted, "
          f"{sum(r['judge'] == 'n' for r in sample)} judge-rejected) -> {a.out}")


if __name__ == "__main__":
    main()
