"""Retrieval ablation: BM25 vs dense vs hybrid, on evals/retrieval_qa.json.

A question is a HIT at k if any of the top-k chunks comes from the expected
document AND contains one of the answer phrases (so a chunk from the right
paper that doesn't actually contain the answer doesn't count).

  python evals/scripts/eval_retrieval.py --kb library_kb.sqlite [--ks 1 3 6] [--json out.json]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))  # shared helpers: scripts/_common.py

from _common import default_paths, open_kb  # noqa: E402

from research_assistant import knowledge  # noqa: E402


def rankings(kb, q, pool):
    """Return {mode: [chunk ids]} for one query."""
    vec = kb._vector_rank(q, pool)
    kw = kb._keyword_rank(q, pool)
    fused = {}
    for ranking in (vec, kw):
        for rank, cid in enumerate(ranking):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (60 + rank)
    hybrid = [c for c, _ in sorted(fused.items(), key=lambda kv: -kv[1])]
    return {"bm25": kw, "dense": vec, "hybrid": hybrid}


def is_hit(kb, chunk_ids, doc, phrases):
    for cid in chunk_ids:
        text, path = kb.db.execute(
            "SELECT c.text, d.path FROM chunks c JOIN docs d ON d.id=c.doc_id WHERE c.id=?", (cid,)
        ).fetchone()
        if Path(path).stem == doc and any(p.lower() in text.lower() for p in phrases):
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kb", default=knowledge.default_kb_path())
    ap.add_argument("--qa", default=default_paths()["qa"])
    ap.add_argument("--ks", type=int, nargs="+", default=[1, 3, 6])
    ap.add_argument("--embedding-model", default=None, help="default: EMBEDDING_MODEL from .env")
    ap.add_argument("--json", default="")
    a = ap.parse_args()

    kb = open_kb(a.kb, a.embedding_model)
    qa = json.load(open(a.qa, encoding="utf-8"))
    modes = ("bm25", "dense", "hybrid")
    hits = {m: {k: 0 for k in a.ks} for m in modes}
    misses = {m: [] for m in modes}
    for r in qa:
        ranked = rankings(kb, r["q"], pool=max(a.ks) * 5)
        for m in modes:
            for k in a.ks:
                if is_hit(kb, ranked[m][:k], r["doc"], r["any"]):
                    hits[m][k] += 1
                elif k == max(a.ks):
                    misses[m].append(r["q"])

    n = len(qa)
    print(f"{n} questions | KB: {kb.stats()}\n")
    print("| method | " + " | ".join(f"recall@{k}" for k in a.ks) + " |")
    print("|---|" + "---|" * len(a.ks))
    for m in modes:
        print(f"| {m} | " + " | ".join(f"{hits[m][k] / n:.0%}" for k in a.ks) + " |")
    if a.json:
        json.dump({"n": n, "hits": hits, "misses": misses}, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
