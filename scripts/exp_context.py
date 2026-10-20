"""Tests B and C (v3): how much source text can qwen3.5:4b use well when it writes one report section?

  python scripts/exp_context.py pool                 # retrieve + grade a fixed passage pool per question (cached)
  python scripts/exp_context.py c [--sizes 4 8 12 16 24] [--repeats 2]   # Test C: passages per section
  python scripts/exp_context.py b [--n 6] [--repeats 2]                  # Test B: neighbour expansion on/off
  python scripts/exp_context.py think [--n 8] [--repeats 2]              # the chosen size again, with thinking on
  python scripts/exp_context.py d [--sizes 8 16] [--repeats 2]           # Test D: how long can a section be?

Every variant writes from the SAME cached pool (evals/v3/exp_pool.json), so only the variable under test changes.
Passages are shuffled with a fixed seed per repeat, so position in the prompt is independent of relevance (that is what
lets "the model skips the middle" be measured). Calls go straight to Ollama for exact token counts, with a 32k window.

Per write: passages given, input tokens, share of passages cited, use by position (first / middle / last third),
citation drift (sentences repair_citations moves), unsupported sentences (wording < MIN_SUPPORT), figure and subject
flags, words, seconds. Results append to evals/v3/exp_context.jsonl.
"""
import argparse
import json
import random
import re
import sqlite3
import sys
import time
import urllib.request

from _common import ROOT, open_kb  # noqa: E402

from research_assistant import deep_report as d  # noqa: E402
from research_assistant import knowledge  # noqa: E402
from research_assistant import report_checks as rc  # noqa: E402

MODEL = "qwen3.5:4b"
OLLAMA = "http://localhost:11434/api/chat"
POOL = ROOT / "evals" / "v3" / "exp_pool.json"
OUT = ROOT / "evals" / "v3" / "exp_context.jsonl"
NUM_CTX = 32_768
QUESTIONS = [
    ("Embedding models: what they are and the datasets used to train them",
     "Which datasets are used to train general-purpose text embedding models?"),
    ("Embedding models: what they are and the datasets used to train them",
     "How are text embedding models trained: objectives, negatives and fine-tuning?"),
    ("How do small language models (1B-8B) learn reliable tool calling: training data, fine-tuning methods and evaluation",
     "What training data and fine-tuning methods give small language models reliable tool calling?"),
    ("How do small language models (1B-8B) learn reliable tool calling: training data, fine-tuning methods and evaluation",
     "How is tool-calling ability of language models evaluated: benchmarks and metrics?"),
]


def chat(prompt: str, json_mode: bool = False, think: bool = False, temperature: float = 0.2, num_predict: int = 2_500) -> dict:
    opts = {"temperature": 0.6, "top_p": 0.95, "top_k": 20} if think else {"temperature": temperature}
    body = {"model": MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False, "think": think,
            "options": {**opts, "num_ctx": NUM_CTX, "num_predict": num_predict + (10_000 if think else 0)}}
    if json_mode:
        body["format"] = "json"
    req = urllib.request.Request(OLLAMA, json.dumps(body).encode(), {"Content-Type": "application/json"})
    t0 = time.time()
    r = json.load(urllib.request.urlopen(req, timeout=1_800))
    return {"text": r["message"].get("content", ""), "seconds": round(time.time() - t0, 1),
            "prompt_tokens": r.get("prompt_eval_count"), "output_tokens": r.get("eval_count")}


# ---- the fixed pool ------------------------------------------------------------------------------------------------

def build_pool(kb_path: str):
    kb = open_kb(kb_path, None)
    llm = lambda p, json_mode=False: chat(p, json_mode, temperature=0)["text"]  # noqa: E731
    pool = []
    for goal, q in QUESTIONS:
        hits = d.retrieve(q, lambda s: kb.search(s, k=12), llm, k=30, per_doc=4)
        graded = []
        for rank, h in enumerate(hits, 1):
            raw = d._obj(d._json(llm(d.RELEVANT_PROMPT.format(
                question=q, goal=goal, source=h["title"], heading=h.get("heading") or "-",
                passage=d._clip(h["text"], d.MAX_PASSAGE_CHARS)), json_mode=True), {}))
            try:
                score = int(raw.get("score", 0))
            except (TypeError, ValueError):
                score = 0
            graded.append({"rank": rank, "score": score, "chunk_id": h["chunk_id"], "title": h["title"],
                           "heading": h.get("heading") or "", "text": h["text"]})
        kept = [g for g in graded if g["score"] >= d.MIN_PASSAGE_SCORE]
        print(f"{q[:70]}: {len(hits)} retrieved, {len(kept)} scored 2+", flush=True)
        pool.append({"goal": goal, "question": q, "passages": graded})
    POOL.write_text(json.dumps(pool, ensure_ascii=False, indent=1), encoding="utf-8")
    print("->", POOL)


def usable(item: dict) -> list[dict]:
    """Passages scoring 2+, best first (score, then retrieval rank); score-1 passages fill up when there are too few."""
    ps = sorted(item["passages"], key=lambda p: (-p["score"], p["rank"]))
    return [p for p in ps if p["score"] >= 1]


# ---- neighbour expansion (Test B) ----------------------------------------------------------------------------------

def neighbours(db: sqlite3.Connection, chunk_id: int, limit: int) -> str:
    """The chunk with the chunks right before and after it in the same document, up to ``limit`` characters."""
    row = db.execute("SELECT doc_id, ord FROM chunks WHERE id=?", (chunk_id,)).fetchone()
    if not row:
        return ""
    doc, order = row
    parts = db.execute("SELECT ord, text FROM chunks WHERE doc_id=? AND ord BETWEEN ? AND ? ORDER BY ord",
                       (doc, order - 1, order + 1)).fetchall()
    text = "\n".join(t for _, t in parts)
    return text if len(text) <= limit else db.execute("SELECT text FROM chunks WHERE id=?", (chunk_id,)).fetchone()[0]


def expand_and_merge(db, chosen: list[dict], limit: int = 4_000) -> list[dict]:
    """Expand each chosen chunk with its neighbours; chunks of one document that are 2 or fewer apart become ONE passage."""
    order = {p["chunk_id"]: db.execute("SELECT doc_id, ord FROM chunks WHERE id=?", (p["chunk_id"],)).fetchone() for p in chosen}
    merged: list[dict] = []
    for p in sorted(chosen, key=lambda p: order[p["chunk_id"]] or (0, 0)):
        doc_ord = order[p["chunk_id"]]
        last = merged[-1] if merged else None
        if last and doc_ord and last["_doc"] == doc_ord[0] and doc_ord[1] - last["_ord"] <= 2:
            gap = db.execute("SELECT text FROM chunks WHERE doc_id=? AND ord > ? AND ord <= ? ORDER BY ord",
                             (doc_ord[0], last["_ord"], doc_ord[1] + 1)).fetchall()
            last["text"] = (last["text"] + "\n" + "\n".join(t for (t,) in gap))[: limit * 2]
            last["_ord"] = doc_ord[1] + 1
            continue
        text = neighbours(db, p["chunk_id"], limit) or p["text"]
        merged.append({**p, "text": text, "_doc": doc_ord[0] if doc_ord else None, "_ord": (doc_ord[1] + 1) if doc_ord else 0})
    return merged


# ---- one write and its measures -------------------------------------------------------------------------------------

def evidence(passages: list[dict]) -> list:
    return [d.Evidence(id=f"E{i}", claim=d.location(p), quote=p["text"], source=p["title"], heading=p["heading"],
                       sub_questions=[0], passage=True) for i, p in enumerate(passages, 1)]


LENGTHS = ("150-300", "400-600", "800-1000")   # Test D targets (the pipeline now uses d.SECTION_WORDS)


def repeats(text: str, threshold: float = 0.6) -> int:
    """Sentences that say nearly the same as an earlier one in the section (content-word overlap >= threshold): the usual
    way a small model fills a length it has no more material for."""
    sents = [rc.content_words(s) for line in text.splitlines() if line.strip() and not line.lstrip().startswith("|")
             for s in rc._sentences(line)]
    sents = [s for s in sents if len(s) >= 5]
    return sum(any(len(a & b) / len(a | b) >= threshold for b in sents[:i]) for i, a in enumerate(sents))


def write_and_measure(item: dict, passages: list[dict], label: str, think: bool = False, length: str = "150-300") -> dict:
    ev = evidence(passages)
    section = {"title": item["question"], "questions": [0], "brief": ""}
    prompt = d.PASSAGE_SECTION_PROMPT.format(title=section["title"], brief="", goal=item["goal"], words=length,
                                             evidence=d._passage_block(ev, limit=10**9))
    r = chat(prompt, think=think)
    body = d._keep_valid_citations(r["text"], {e.id for e in ev})
    stats: dict = {}
    repaired = rc.repair_citations(d._clean_prose(body, section["title"]), ev, stats)
    labelled = rc.label_text(repaired, {e.id: e for e in ev}, rc.evidence_numbers(ev), flags_only=True)
    cited = {f"E{n}" for n in re.findall(r"\[E(\d+)\]", body)}
    n = len(ev)
    thirds = [range(1, n // 3 + 1), range(n // 3 + 1, 2 * n // 3 + 1), range(2 * n // 3 + 1, n + 1)]
    use = [round(sum(f"E{i}" in cited for i in t) / max(len(t), 1), 2) for t in thirds]
    return {"test": label, "question": item["question"][:60], "passages": n, "think": think,
            "input_chars": sum(len(p["text"]) for p in passages), "prompt_tokens": r["prompt_tokens"],
            "output_tokens": r["output_tokens"], "seconds": r["seconds"], "words": len(re.sub(r"\[E\d+\]", "", body).split()),
            "cited_share": round(len(cited) / max(n, 1), 2), "use_first_mid_last": use,
            "cited_sentences": stats.get("cited", 0), "drift": stats.get("repaired", 0),
            "unsupported": labelled.count("[cited; wording"), "figure_flags": labelled.count("[cited; figure"),
            "subject_flags": labelled.count("[cited; subject"), "uncited": labelled.count("[inference"),
            "length_target": length, "repeats": repeats(repaired)}


def log(row: dict):
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(json.dumps(row, ensure_ascii=False), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("test", choices=["pool", "c", "b", "think", "d"])
    ap.add_argument("--kb", default=knowledge.default_kb_path())
    ap.add_argument("--sizes", type=int, nargs="+", default=[4, 8, 12, 16, 24])
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--repeats", type=int, default=2)
    a = ap.parse_args()
    if a.test == "pool":
        return build_pool(a.kb)
    pool = json.loads(POOL.read_text(encoding="utf-8"))
    db = sqlite3.connect(f"file:{a.kb}?mode=ro", uri=True)
    for rep in range(a.repeats):
        for qi, item in enumerate(pool):
            ps = usable(item)
            rng = random.Random(1000 * rep + qi)
            if a.test == "c":
                for size in a.sizes:
                    if size > len(ps):
                        print(f"skip {size}: only {len(ps)} usable passages for {item['question'][:50]}", file=sys.stderr)
                        continue
                    chosen = ps[:size]
                    rng.shuffle(chosen)
                    log({**write_and_measure(item, chosen, "C"), "repeat": rep})
            elif a.test == "d":                              # best-first, as the pipeline gives them since Test C
                for size in a.sizes:
                    for length in LENGTHS:
                        log({**write_and_measure(item, ps[:size], "D", length=length), "repeat": rep})
            elif a.test == "b":
                chosen = ps[: a.n]
                for expand in (False, True):
                    given = expand_and_merge(db, chosen) if expand else list(chosen)
                    random.Random(1000 * rep + qi).shuffle(given)
                    log({**write_and_measure(item, given, "B-expand" if expand else "B-plain"), "repeat": rep, "chosen": a.n})
            else:
                chosen = ps[: a.n]
                rng.shuffle(chosen)
                log({**write_and_measure(item, chosen, "think", think=True), "repeat": rep})


if __name__ == "__main__":
    main()
