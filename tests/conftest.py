"""Shared test setup."""
import pytest

from research_assistant import rerank


@pytest.fixture(autouse=True)
def no_real_reranker(monkeypatch):
    """Reranking is on by default (2026-10-20), so a graph run would load the 2 GB cross-encoder. Tests get a fake one that
    keeps the hybrid order: the reranking code path still runs, offline and instantly."""
    fake = rerank.Reranker("fake", score_fn=lambda q, texts: [-float(i) for i in range(len(texts))])
    monkeypatch.setattr(rerank, "get", lambda model=rerank.DEFAULT_MODEL: fake)
