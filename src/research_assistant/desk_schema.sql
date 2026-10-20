-- Research Desk database: <vault>/.desk/desk.sqlite. The ONE schema for both writers:
--   Python (desk.py) writes the run trace: runs, steps, llm_calls, retrievals, judgements, evidence, section_inputs, sentences.
--   The dashboard (lib/desk.ts) writes feedback.
-- Kept apart from the library database, which is rebuilt when the library is re-embedded: feedback must never be lost.
-- Every statement is idempotent (IF NOT EXISTS), so either side may create the file. Bump user_version on a change.

PRAGMA user_version = 2;

CREATE TABLE IF NOT EXISTS runs (
    run_id       TEXT PRIMARY KEY,           -- the LangGraph thread id (or "cli-..." for script runs)
    goal         TEXT NOT NULL DEFAULT '',
    title        TEXT NOT NULL DEFAULT '',
    engine       TEXT NOT NULL DEFAULT '',   -- e.g. v3.0-hybrid: feedback is compared per engine version
    model        TEXT NOT NULL DEFAULT '',
    settings     TEXT NOT NULL DEFAULT '{}', -- JSON: the run's options
    plan         TEXT NOT NULL DEFAULT '{}', -- JSON: title, questions, outline
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    outcome      TEXT NOT NULL DEFAULT 'running',   -- running | complete | failed | stopped
    error        TEXT NOT NULL DEFAULT '',
    report_path  TEXT NOT NULL DEFAULT '',
    stats        TEXT NOT NULL DEFAULT '{}'  -- JSON
);

CREATE TABLE IF NOT EXISTS steps (
    id           INTEGER PRIMARY KEY,
    run_id       TEXT NOT NULL,
    name         TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    seconds      REAL,
    outcome      TEXT NOT NULL DEFAULT 'running',   -- running | ok | paused (waiting for the user) | failed | stopped
    error        TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS llm_calls (
    id           INTEGER PRIMARY KEY,
    run_id       TEXT NOT NULL,
    step         TEXT NOT NULL DEFAULT '',
    role         TEXT NOT NULL DEFAULT '',   -- planner | extractor (passage judge) | writer | thinker
    started_at   TEXT NOT NULL,
    seconds      REAL NOT NULL,
    prompt_chars INTEGER NOT NULL,
    answer_chars INTEGER NOT NULL,
    json_mode    INTEGER NOT NULL,
    ok           INTEGER NOT NULL            -- 0 = every attempt failed (the pipeline got "")
);

-- Every chunk retrieval returned for a sub-question, in rank order, with why it ranked there.
CREATE TABLE IF NOT EXISTS retrievals (
    id            INTEGER PRIMARY KEY,
    run_id        TEXT NOT NULL,
    question_idx  INTEGER NOT NULL,
    question      TEXT NOT NULL,
    queries       TEXT NOT NULL DEFAULT '[]',  -- JSON: the question plus model-written variants actually searched
    rank          INTEGER NOT NULL,            -- 1-based, after fusing the queries
    chunk_id      INTEGER,                     -- library chunks.id (changes when the library is rebuilt: see text_hash)
    text_hash     TEXT NOT NULL DEFAULT '',    -- stable identity of the chunk text across rebuilds
    doc_title     TEXT NOT NULL DEFAULT '',
    doc_path      TEXT NOT NULL DEFAULT '',
    heading       TEXT NOT NULL DEFAULT '',
    fused_score   REAL,
    vector_rank   INTEGER,                     -- rank in the meaning search of the first query that found it (NULL = not found)
    keyword_rank  INTEGER,                     -- rank in the keyword (BM25) search of that query
    hybrid_rank   INTEGER,                     -- M3: rank before the reranker (rank above is then the reranker's)
    rerank_score  REAL                         -- M3: the cross-encoder's score (NULL without the reranker)
);

-- The relevance grade the model gave each retrieved chunk for its question.
CREATE TABLE IF NOT EXISTS judgements (
    id            INTEGER PRIMARY KEY,
    run_id        TEXT NOT NULL,
    question_idx  INTEGER NOT NULL,
    chunk_id      INTEGER,
    text_hash     TEXT NOT NULL DEFAULT '',
    doc_title     TEXT NOT NULL DEFAULT '',
    score         INTEGER NOT NULL,            -- 0-3; -1 = already kept for an earlier question (not judged again)
    kept          INTEGER NOT NULL,
    eid           TEXT NOT NULL DEFAULT ''     -- E-number in the report when kept
);

-- The evidence the report cites: E-number -> library chunk.
CREATE TABLE IF NOT EXISTS evidence (
    run_id        TEXT NOT NULL,
    eid           TEXT NOT NULL,
    chunk_id      INTEGER,
    text_hash     TEXT NOT NULL DEFAULT '',
    doc_title     TEXT NOT NULL DEFAULT '',
    doc_path      TEXT NOT NULL DEFAULT '',
    heading       TEXT NOT NULL DEFAULT '',
    url           TEXT NOT NULL DEFAULT '',
    kind          TEXT NOT NULL DEFAULT '',
    questions     TEXT NOT NULL DEFAULT '[]',  -- JSON: question indexes this chunk was kept for
    PRIMARY KEY (run_id, eid)
);

-- What each section's writer was given (included = 0: did not fit the context budget).
CREATE TABLE IF NOT EXISTS section_inputs (
    id            INTEGER PRIMARY KEY,
    run_id        TEXT NOT NULL,
    section       TEXT NOT NULL,
    position      INTEGER NOT NULL,
    eid           TEXT NOT NULL,
    included      INTEGER NOT NULL,
    prompt_chars  INTEGER NOT NULL DEFAULT 0
);

-- Every sentence of the finished report, with the evidence it cites and any check flag.
CREATE TABLE IF NOT EXISTS sentences (
    id            INTEGER PRIMARY KEY,
    run_id        TEXT NOT NULL,
    section       TEXT NOT NULL,
    position      INTEGER NOT NULL,            -- order within the section
    sentence_key  TEXT NOT NULL,               -- stable id for feedback: hash of run, section and text
    text          TEXT NOT NULL,
    cites         TEXT NOT NULL DEFAULT '[]',  -- JSON: E-numbers
    flag          TEXT NOT NULL DEFAULT ''     -- figure | subject | wording | domain | inference | '' (passed)
);

-- One row per click. Append-only: a changed mind is a new row (the latest per target wins); 'cleared' withdraws it.
CREATE TABLE IF NOT EXISTS feedback (
    id            INTEGER PRIMARY KEY,
    created_at    TEXT NOT NULL,
    run_id        TEXT NOT NULL DEFAULT '',
    engine        TEXT NOT NULL DEFAULT '',
    report_slug   TEXT NOT NULL DEFAULT '',
    target        TEXT NOT NULL CHECK (target IN ('report', 'section', 'sentence', 'chunk', 'answer')),
    target_ref    TEXT NOT NULL,               -- report: slug · section: title · sentence: sentence_key · chunk: E-number
    rating        TEXT NOT NULL CHECK (rating IN ('relevant', 'not_relevant', 'wrong_subject', 'wrong', 'helpful',
                                                  'partly', 'not_helpful', 'cleared')),
    reason        TEXT NOT NULL DEFAULT '',
    section       TEXT NOT NULL DEFAULT '',
    question      TEXT NOT NULL DEFAULT '',
    eid           TEXT NOT NULL DEFAULT '',
    chunk_id      INTEGER,
    text_hash     TEXT NOT NULL DEFAULT '',
    doc_title     TEXT NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS steps_run ON steps (run_id);
CREATE INDEX IF NOT EXISTS llm_calls_run ON llm_calls (run_id);
CREATE INDEX IF NOT EXISTS retrievals_run ON retrievals (run_id, question_idx);
CREATE INDEX IF NOT EXISTS judgements_run ON judgements (run_id, question_idx);
CREATE INDEX IF NOT EXISTS section_inputs_run ON section_inputs (run_id);
CREATE INDEX IF NOT EXISTS sentences_run ON sentences (run_id, section);
CREATE INDEX IF NOT EXISTS feedback_run ON feedback (run_id, target, target_ref);
CREATE INDEX IF NOT EXISTS feedback_chunk ON feedback (text_hash);
