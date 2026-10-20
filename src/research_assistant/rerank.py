"""Cross-encoder reranking (M3): reorder the hybrid search pool by reading each (question, passage) pair together.

Hybrid search (BM25 + vectors) is fast but scores the question and the passage separately. A cross-encoder reads them
side by side and is much better at "does this passage answer this question". The pipeline retrieves a wider pool
(RERANK_POOL), the reranker keeps the best k, and only those go on to the model's 0-3 relevance grade.

Runs on the CPU with plain `transformers` (the shared venv's torch is the CPU build; the GPU stays with the LLM): about
1.6 s for 24 passages with bge-reranker-base, measured 2026-10-20. Models are loaded once per process.
"""
import threading
from collections.abc import Callable

DEFAULT_MODEL = "BAAI/bge-reranker-v2-m3"     # multilingual (covers Telugu); bge-reranker-base is the faster English one
RERANK_POOL = 24                               # hybrid candidates read by the reranker per question
MAX_LENGTH = 512                               # tokens per (question, passage) pair; chunks are <= ~450 tokens
BATCH = 16

_MODELS: dict[str, "Reranker"] = {}
_LOCK = threading.Lock()


class Reranker:
    """``score_fn(query, texts) -> scores`` can be injected (tests); otherwise the model is loaded on first use."""

    def __init__(self, model: str = DEFAULT_MODEL, score_fn: Callable[[str, list[str]], list[float]] | None = None):
        self.model_name = model
        self._score_fn = score_fn
        self._tok = self._model = None

    def _load(self):
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self._tok = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name).eval()

    def scores(self, query: str, texts: list[str]) -> list[float]:
        if self._score_fn is not None:
            return list(self._score_fn(query, texts))
        import torch

        with _LOCK:
            if self._model is None:
                self._load()
            out: list[float] = []
            with torch.inference_mode():
                for i in range(0, len(texts), BATCH):
                    batch = texts[i:i + BATCH]
                    enc = self._tok([query] * len(batch), batch, padding=True, truncation=True, max_length=MAX_LENGTH,
                                    return_tensors="pt")
                    out += self._model(**enc).logits.view(-1).float().tolist()
            return out

    def rerank(self, query: str, hits: list[dict], top: int) -> list[dict]:
        """The ``top`` best hits by cross-encoder score, best first. Each hit gains ``rerank_score``; the order before
        reranking stays in ``hybrid_rank`` (1-based) so the trace can show what the reranker changed."""
        if not hits:
            return []
        scored = [{**h, "hybrid_rank": i, "rerank_score": round(s, 4)}
                  for i, (h, s) in enumerate(zip(hits, self.scores(query, [h["text"] for h in hits]), strict=True), 1)]
        return sorted(scored, key=lambda h: -h["rerank_score"])[:top]


def get(model: str = DEFAULT_MODEL) -> Reranker:
    """One loaded model per name per process (loading takes ~10-15 s)."""
    with _LOCK:
        if model not in _MODELS:
            _MODELS[model] = Reranker(model)
        return _MODELS[model]
