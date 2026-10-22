"""Test A (v3): which chunk size retrieves best? Re-chunks the frozen retrieval corpus at several sizes and runs the
retrieval questions (evals/retrieval_qa.json) against each, with the same hybrid search the pipeline uses.

  python evals/scripts/exp_chunk_size.py [--sizes 600 1000 1400 1800 2500 3500] [--out evals/v3/exp_a_chunk_size.json]

Two measures, because bigger chunks contain the answer phrase more easily:
  recall@k        the answer is in one of the top k chunks (k = 1, 3, 6)
  recall@budget   the answer is in the top chunks that fit in N characters of reading (2,000 / 4,000 / 8,000): equal cost
A hit needs the expected document AND an answer phrase in the chunk (as in eval_retrieval.py).
"""
import argparse
import functools
import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))  # shared helpers: scripts/_common.py

from _common import ROOT, default_paths  # noqa: E402

from research_assistant import knowledge  # noqa: E402
from research_assistant.documents import make_embeddings  # noqa: E402

SOURCE = ROOT / "evals" / "kb" / "retrieval_v1.sqlite"
BUDGETS = (2_000, 4_000, 8_000)
KS = (1, 3, 6)


class Batched:
    """Embeddings in batches of 32 with retries: one request holding a whole document's chunks (hundreds at small chunk
    sizes) made Ollama's embedding runner fail ("connection refused" on /tokenize, 2026-10-19)."""

    def __init__(self, inner, size: int = 32, tries: int = 4):
        self.inner, self.size, self.tries = inner, size, tries

    def _retry(self, fn, arg):
        for attempt in range(self.tries):
            try:
                return fn(arg)
            except Exception:
                if attempt == self.tries - 1:
                    raise
                time.sleep(3 * (attempt + 1))

    def embed_documents(self, texts):
        out = []
        for i in range(0, len(texts), self.size):
            out += self._retry(self.inner.embed_documents, texts[i:i + self.size])
        return out

    def embed_query(self, text):
        return self._retry(self.inner.embed_query, text)


def hybrid(kb, q, pool=60):
    fused: dict[int, float] = {}
    for ranking in (kb._vector_rank(q, pool), kb._keyword_rank(q, pool)):
        for rank, cid in enumerate(ranking):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (60 + rank)
    return [c for c, _ in sorted(fused.items(), key=lambda kv: -kv[1])]


def score(kb, qa) -> dict:
    hits_k = {k: 0 for k in KS}
    hits_b = {b: 0 for b in BUDGETS}
    for item in qa:
        ranked = hybrid(kb, item["q"])
        rows = [kb.db.execute("SELECT c.text, d.path FROM chunks c JOIN docs d ON d.id=c.doc_id WHERE c.id=?", (cid,)).fetchone()
                for cid in ranked[:40]]
        hit = [Path(path).stem == item["doc"] and any(p.lower() in text.lower() for p in item["any"]) for text, path in rows]
        for k in KS:
            hits_k[k] += any(hit[:k])
        for b in BUDGETS:
            used, found = 0, False
            for (text, _), h in zip(rows, hit, strict=True):
                if used and used + len(text) > b:
                    break
                used += len(text)
                found = found or h
            hits_b[b] += found
    n = len(qa)
    return {"recall_at_k": {k: round(v / n, 3) for k, v in hits_k.items()},
            "recall_at_budget": {b: round(v / n, 3) for b, v in hits_b.items()}}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sizes", type=int, nargs="+", default=[600, 1000, 1400, 1800, 2500, 3500])
    ap.add_argument("--out", default=str(ROOT / "evals" / "v3" / "exp_a_chunk_size.json"))
    a = ap.parse_args()
    qa = json.loads(Path(default_paths()["qa"]).read_text(encoding="utf-8"))
    src = sqlite3.connect(f"file:{SOURCE}?mode=ro", uri=True)
    docs = src.execute("SELECT path, title, markdown FROM docs").fetchall()
    model = src.execute("SELECT value FROM meta WHERE key='embedding_model'").fetchone()[0]
    emb = Batched(make_embeddings(model))
    results = {"questions": len(qa), "documents": len(docs), "embedding_model": model, "sizes": {}}
    real = knowledge.chunk_markdown
    for size in a.sizes:
        t0 = time.time()
        knowledge.chunk_markdown = functools.partial(real, max_chars=size, max_table_chars=max(size, 1_500))
        try:
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
                kb = knowledge.KnowledgeBase(Path(tmp) / "kb.sqlite", emb, embedding_model=model)
                for path, title, md in docs:
                    kb.ingest_text(path, md, title=title)
                chunks, avg = kb.db.execute("SELECT count(*), avg(length(text)) FROM chunks").fetchone()
                r = score(kb, qa)
                kb.close()
        finally:
            knowledge.chunk_markdown = real
        results["sizes"][size] = {"chunks": chunks, "avg_chars": round(avg), **r, "seconds": round(time.time() - t0)}
        print(f"size {size:5}: {chunks:5} chunks, avg {avg:5.0f} chars | recall@1/3/6 "
              f"{'/'.join(f'{v:.0%}' for v in r['recall_at_k'].values())} | recall@2k/4k/8k chars "
              f"{'/'.join(f'{v:.0%}' for v in r['recall_at_budget'].values())} | {time.time() - t0:.0f}s", flush=True)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(results, indent=1), encoding="utf-8")
    print("->", a.out)


if __name__ == "__main__":
    main()
