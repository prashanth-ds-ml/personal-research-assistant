"""M3 offline test: does a cross-encoder reranker put the answering chunk higher than hybrid search alone?

  python scripts/exp_rerank.py [--models BAAI/bge-reranker-base BAAI/bge-reranker-v2-m3] [--out evals/v3/exp_rerank.json]

Frozen retrieval corpus and questions (as eval_retrieval.py / exp_chunk_size.py): the hybrid top RERANK_POOL chunks per
question are reranked; recall@1/3/6 is compared with the hybrid order. A hit needs the expected document AND an answer
phrase in the chunk. Also reports the reranker's CPU time per question.
"""
import argparse
import json
import time
from pathlib import Path

from _common import ROOT, default_paths, open_kb  # noqa: E402
from exp_chunk_size import hybrid  # noqa: E402

from research_assistant import rerank  # noqa: E402

KB = ROOT / "evals" / "kb" / "retrieval_v1.sqlite"
KS = (1, 3, 6)


def recall(rows_in_order, item) -> dict:
    hit = [Path(path).stem == item["doc"] and any(p.lower() in text.lower() for p in item["any"]) for _, text, path in rows_in_order]
    return {k: any(hit[:k]) for k in KS}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--models", nargs="+", default=["BAAI/bge-reranker-base", "BAAI/bge-reranker-v2-m3"])
    ap.add_argument("--out", default=str(ROOT / "evals" / "v3" / "exp_rerank.json"))
    a = ap.parse_args()
    qa = json.loads(Path(default_paths()["qa"]).read_text(encoding="utf-8"))
    kb = open_kb(str(KB), None)
    pools = []
    for item in qa:
        ids = hybrid(kb, item["q"])[: rerank.RERANK_POOL]
        rows = [(cid, *kb.db.execute("SELECT c.text, d.path FROM chunks c JOIN docs d ON d.id=c.doc_id WHERE c.id=?",
                                     (cid,)).fetchone()) for cid in ids]
        pools.append((item, rows))
    n = len(qa)
    results = {"questions": n, "pool": rerank.RERANK_POOL, "hybrid": {}, "models": {}}
    base = {k: sum(recall(rows, item)[k] for item, rows in pools) / n for k in KS}
    results["hybrid"] = {k: round(v, 3) for k, v in base.items()}
    print(f"hybrid (no reranker): recall@1/3/6 {'/'.join(f'{v:.0%}' for v in base.values())}", flush=True)
    for name in a.models:
        rr = rerank.Reranker(name)
        t0 = time.time()
        rr.scores("warm up", ["load the model once"])
        load = time.time() - t0
        got = {k: 0 for k in KS}
        secs = []
        for item, rows in pools:
            t0 = time.time()
            scores = rr.scores(item["q"], [text for _, text, _ in rows])
            secs.append(time.time() - t0)
            order = [r for _, r in sorted(zip(scores, rows, strict=True), key=lambda x: -x[0])]
            for k, ok in recall(order, item).items():
                got[k] += ok
        results["models"][name] = {"recall": {k: round(v / n, 3) for k, v in got.items()}, "load_seconds": round(load, 1),
                                   "seconds_per_question": round(sum(secs) / n, 2)}
        print(f"{name}: recall@1/3/6 {'/'.join(f'{got[k] / n:.0%}' for k in KS)} | load {load:.0f}s | "
              f"{sum(secs) / n:.1f}s per question (CPU, {rerank.RERANK_POOL} passages)", flush=True)
    Path(a.out).write_text(json.dumps(results, indent=1), encoding="utf-8")
    print("->", a.out)


if __name__ == "__main__":
    main()
