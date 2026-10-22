"""Re-judge the labelled faithfulness sheet with another model and compare error types.

  python evals/scripts/rejudge_sheet.py --model gemma4:e4b [--labels claude]

Uses the FULL passage (the KB chunk the quote came from), exactly as the pipeline's judge
does, not the short context window stored in the sheet.
"""
import argparse
import csv
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

from research_assistant import deep_report as d  # noqa: E402
from research_assistant import knowledge  # noqa: E402


def chunk_for(db, row) -> str:
    hit = db.execute(
        "SELECT c.text FROM chunks c JOIN docs d ON d.id=c.doc_id WHERE c.text LIKE ? AND d.title LIKE ? LIMIT 1",
        ("%" + row["quote"][:40].replace("%", "") + "%", row["source"][:25] + "%")).fetchone()
    return hit[0] if hit else row["context"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--sheet", default=str(ROOT / "evals" / "faithfulness_sheet.csv"))
    ap.add_argument("--labels", default="human", help="column holding the ground truth: human or claude")
    a = ap.parse_args()

    db = sqlite3.connect(knowledge.default_kb_path())
    rows = list(csv.DictReader(open(a.sheet, encoding="utf-8-sig")))
    llm = d.ollama_llm(a.model, os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"), temperature=0)
    tp = fp = tn = fn = 0
    flips = []
    for r in rows:
        truth = r[a.labels].strip().lower()
        if truth not in ("y", "n"):
            continue
        verdict = "y" if d._entailed(r["claim"], r["quote"], chunk_for(db, r), llm) else "n"
        if verdict != r["judge"]:
            flips.append((r["id"], r["judge"], verdict, truth))
        tp += verdict == "y" and truth == "y"
        fp += verdict == "y" and truth == "n"
        tn += verdict == "n" and truth == "n"
        fn += verdict == "n" and truth == "y"
    n = tp + fp + tn + fn
    print(f"judge model: {a.model} | ground truth: {a.labels} column | n={n}")
    print(f"accuracy {(tp + tn) / n:.0%} | false accepts {fp} (of {tp + fp} accepted) | "
          f"false rejects {fn} (of {tp + fn} truly supported) | recall of supported {tp / max(tp + fn, 1):.0%}")
    print("verdict changed vs the llama judge in the sheet (id, sheet, now, truth):", flips)


if __name__ == "__main__":
    main()
