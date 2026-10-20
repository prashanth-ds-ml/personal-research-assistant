"""M3 reranker: reorders the hybrid pool, keeps the best k, and is recorded in the trace and the engine version."""
import json
import sqlite3

from research_assistant import deep_report, desk, rerank
from research_assistant.configuration import Configuration


def hit(i, text):
    return {"title": f"Doc {i}", "heading": "", "text": text, "path": f"d{i}.md", "chunk_id": 100 + i,
            "source_url": "", "source_kind": "pdf"}


def by_keyword(word):
    """A fake cross-encoder: passages containing ``word`` score high."""
    return rerank.Reranker("fake", score_fn=lambda q, texts: [5.0 if word in t else -1.0 for t in texts])


def test_R_T01_rerank_puts_the_answering_passage_first_and_keeps_both_ranks():
    hits = [hit(1, "general embeddings text"), hit(2, "CCPairs from Reddit"), hit(3, "unrelated")]
    out = by_keyword("CCPairs").rerank("which datasets?", hits, top=2)
    assert [h["title"] for h in out] == ["Doc 2", "Doc 1"]
    assert out[0]["hybrid_rank"] == 2 and out[0]["rerank_score"] == 5.0


def test_R_T02_the_pipeline_reads_a_wider_pool_and_keeps_the_reranked_best(tmp_path):
    pool = [hit(i, "filler passage about search") for i in range(1, 30)]
    pool[20]["text"] = "CCPairs is the answer"                                  # far down the hybrid order
    seen_k = []

    def search(q):
        return pool

    def retrieve_spy(q, search, llm, k=8, per_doc=3, n_queries=3, queries_out=None):
        seen_k.append(k)
        queries_out.extend([q])
        return pool[:k]

    plan = deep_report.Plan(goal="g", title="t", sub_questions=["which datasets?"], outline=[])
    trace = desk.RunTrace(str(tmp_path), "r1")
    trace.start_run("g")
    real = deep_report.retrieve
    deep_report.retrieve = retrieve_spy
    try:
        with trace.step("research"):
            ev = deep_report.gather_passages(plan, search, lambda p, json_mode=False: json.dumps({"score": 2}), k=8,
                                             reranker=by_keyword("CCPairs"))
    finally:
        deep_report.retrieve = real
    assert seen_k == [rerank.RERANK_POOL]                                       # a pool of 24, not 8
    assert ev[0].quote == "CCPairs is the answer" and len(ev) == 8               # reranked best first, 8 kept
    rows = sqlite3.connect(desk.db_path(str(tmp_path))).execute(
        "select rank, hybrid_rank, rerank_score from retrievals order by rank").fetchall()
    assert len(rows) == rerank.RERANK_POOL and rows[0] == (1, 21, 5.0)           # the whole pool is traced


def test_R_T03_on_by_default_and_the_engine_version_says_when_it_is_on():
    assert Configuration().rerank is True                                         # default since 2026-10-20
    assert deep_report.engine_version(False) == "v3.0-hybrid" and deep_report.engine_version(True) == "v3.1-rerank"


def test_R_T04_an_old_desk_database_gains_the_rerank_columns(tmp_path):
    path = tmp_path / "old.sqlite"
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE retrievals (id INTEGER PRIMARY KEY, run_id TEXT, question_idx INTEGER, question TEXT, "
                "queries TEXT, rank INTEGER, chunk_id INTEGER, text_hash TEXT, doc_title TEXT, doc_path TEXT, heading TEXT, "
                "fused_score REAL, vector_rank INTEGER, keyword_rank INTEGER)")
    con.commit()
    con.close()
    cols = {r[1] for r in desk.connect(path).execute("pragma table_info(retrievals)")}
    assert {"hybrid_rank", "rerank_score"} <= cols
