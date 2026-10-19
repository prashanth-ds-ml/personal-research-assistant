"""The Research Desk database: a trace of every run and the user's feedback, in ``<vault>/.desk/desk.sqlite``.

The schema lives in ``desk_schema.sql`` and is shared with the dashboard (which writes the feedback). This module writes the
trace: the run, its steps, every model call, every retrieved chunk with its ranks, every relevance grade, the evidence the
report cites, what each section's writer was given, and every sentence of the report with its citations and flags.

Tracing must never break a run: every write swallows database and file errors (one warning per run). The current run's
trace travels in a context variable (``CURRENT``) set by each graph step, so two runs never write into each other's trace.
"""

import contextlib
import contextvars
import hashlib
import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

DESK_DIR = ".desk"
DB_NAME = "desk.sqlite"
SCHEMA = Path(__file__).with_name("desk_schema.sql")
META_SECTIONS = {"evidence status", "limitations", "sources", "evidence appendix"}
_CITE = re.compile(r"\[(E\d+)\]")
_FLAGS = (("[cited; figure", "figure"), ("[cited; subject", "subject"), ("[cited; wording", "wording"), ("[inference", "inference"))
_TAG_ONLY = re.compile(r"^\s*\[(cited;|inference|established|single source)[^\]]*\]\s*$")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def db_path(vault_path: str) -> Path | None:
    return Path(vault_path) / DESK_DIR / DB_NAME if vault_path else None


def text_hash(text: str) -> str:
    """Identity of a chunk's text that survives a library rebuild (chunk ids do not)."""
    return hashlib.sha1(re.sub(r"\s+", " ", text or "").strip().lower().encode("utf-8")).hexdigest()[:16]


_READY: set[str] = set()      # database files whose schema this process has already applied


def connect(path: Path) -> sqlite3.Connection:
    """Open (and if needed create) the desk database with the shared schema (applied once per file per process)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    key, existed = str(path.resolve()), path.exists()
    con = sqlite3.connect(path, timeout=10)
    con.execute("PRAGMA busy_timeout=10000")
    if key not in _READY or not existed:                # a deleted file is recreated with its schema
        con.execute("PRAGMA journal_mode=WAL")        # the dashboard reads and writes feedback while a run writes its trace
        con.executescript(SCHEMA.read_text(encoding="utf-8"))
        _READY.add(key)
    return con


def report_sentences(report_md: str) -> list[dict]:
    """Every prose sentence of a finished report, by section, with its citations and check flag. Tables, headings,
    quotes and the meta sections (status, limitations, sources, appendix) are left out."""
    from research_assistant.report_checks import (
        _sentences,  # same splitter the labels use
    )

    out, section = [], ""
    position = 0
    for line in report_md.splitlines():
        if line.startswith("## "):
            section, position = line[3:].strip(), 0
            continue
        stripped = line.strip()
        if (not section or section.lower() in META_SECTIONS or not stripped
                or stripped.startswith(("|", "#", ">", "```", "*The library", "*This report", "*The model"))):
            continue
        pieces: list[str] = []
        for piece in _sentences(stripped.lstrip("-*0123456789. ")):
            if pieces and _TAG_ONLY.match(piece):           # "... [E2]. [cited; ...]": the flag belongs to the sentence
                pieces[-1] = pieces[-1].rstrip() + " " + piece.strip()
            else:
                pieces.append(piece)
        for sent in pieces:
            if len(sent.split()) < 4:
                continue
            flag = next((name for tag, name in _FLAGS if tag in sent), "")
            clean = re.sub(r"\s*\[(cited;[^\]]*|inference[^\]]*|established|single source)\]", "", sent).strip()
            position += 1
            out.append({"section": section, "position": position, "text": clean,
                        "cites": list(dict.fromkeys(_CITE.findall(sent))), "flag": flag})
    return out


class RunTrace:
    """Writes one run's trace. ``RunTrace("", "")`` (or a missing vault / run id) is a silent no-op."""

    def __init__(self, vault_path: str, run_id: str):
        self.path = db_path(vault_path)
        self.run_id = run_id
        self.enabled = bool(self.path) and bool(run_id)
        self.step_name = ""
        self._warned = False

    def _write(self, sql: str, rows: list[tuple] | tuple = ()) -> None:
        if not self.enabled:
            return
        try:
            with contextlib.closing(connect(self.path)) as con, con:
                if rows and isinstance(rows, list):
                    con.executemany(sql, rows)
                else:
                    con.execute(sql, rows)
        except (sqlite3.Error, OSError) as e:
            if not self._warned:
                print(f"Warning: run trace not written ({str(e)[:120]}); the run continues")
                self._warned = True

    # -- the run -----------------------------------------------------------------------------------------------------
    def start_run(self, goal: str, engine: str = "", model: str = "", settings: dict | None = None) -> None:
        """Idempotent: the first step of every graph invocation calls it; only the first call creates the row."""
        self._write("INSERT OR IGNORE INTO runs (run_id, goal, engine, model, settings, started_at) VALUES (?,?,?,?,?,?)",
                    (self.run_id, goal, engine, model, json.dumps(settings or {}, default=str), now()))

    def set_plan(self, plan: dict) -> None:
        self._write("UPDATE runs SET title=?, plan=? WHERE run_id=?",
                    (str(plan.get("title", "")), json.dumps(plan, default=str), self.run_id))

    def finish_run(self, outcome: str, report_path: str = "", stats: dict | None = None, error: str = "") -> None:
        self._write("UPDATE runs SET outcome=?, finished_at=?, report_path=?, stats=?, error=? WHERE run_id=?",
                    (outcome, now(), report_path, json.dumps(stats or {}, default=str), error[:1000], self.run_id))

    @contextlib.contextmanager
    def step(self, name: str):
        """Record a graph step's start, end, duration and outcome; sets this trace as the current one meanwhile."""
        self.step_name = name
        started, t0 = now(), time.monotonic()
        token = CURRENT.set(self)
        outcome, error = "ok", ""
        try:
            yield self
        except BaseException as e:
            from langgraph.errors import (
                GraphBubbleUp,  # a pause for the user, not a failure
            )

            outcome = ("paused" if isinstance(e, GraphBubbleUp)
                       else "stopped" if type(e).__name__ == "RunStopped" else "failed")
            error = "" if outcome != "failed" else f"{type(e).__name__}: {str(e)[:500]}"
            raise
        finally:
            CURRENT.reset(token)
            self._write("INSERT INTO steps (run_id, name, started_at, finished_at, seconds, outcome, error) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (self.run_id, name, started, now(), round(time.monotonic() - t0, 3), outcome, error))

    # -- model calls -------------------------------------------------------------------------------------------------
    def llm_call(self, role: str, seconds: float, prompt: str, answer: str, json_mode: bool, ok: bool,
                 started_at: str = "") -> None:
        self._write("INSERT INTO llm_calls (run_id, step, role, started_at, seconds, prompt_chars, answer_chars, json_mode, ok) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (self.run_id, self.step_name, role, started_at or now(), round(seconds, 3), len(prompt), len(answer),
                     int(json_mode), int(ok)))

    # -- evidence ------------------------------------------------------------------------------------------------------
    def retrievals(self, question_idx: int, question: str, queries: list[str], hits: list[dict]) -> None:
        q = json.dumps(queries, ensure_ascii=False)
        self._write("INSERT INTO retrievals (run_id, question_idx, question, queries, rank, chunk_id, text_hash, doc_title, "
                    "doc_path, heading, fused_score, vector_rank, keyword_rank) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [(self.run_id, question_idx, question, q, rank, h.get("chunk_id"), text_hash(h.get("text", "")),
                      h.get("title", ""), h.get("path", ""), h.get("heading") or "", h.get("fused"), h.get("vector_rank"),
                      h.get("keyword_rank")) for rank, h in enumerate(hits, 1)])

    def judgement(self, question_idx: int, hit: dict, score: int, kept: bool, eid: str = "") -> None:
        self._write("INSERT INTO judgements (run_id, question_idx, chunk_id, text_hash, doc_title, score, kept, eid) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (self.run_id, question_idx, hit.get("chunk_id"), text_hash(hit.get("text", "")), hit.get("title", ""),
                     score, int(kept), eid))

    def evidence(self, items: list) -> None:
        """The report's evidence (deep_report.Evidence items), E-number -> chunk. Replaces what was recorded before."""
        self._write("DELETE FROM evidence WHERE run_id=?", (self.run_id,))
        self._write("INSERT INTO evidence (run_id, eid, chunk_id, text_hash, doc_title, doc_path, heading, url, kind, questions) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    [(self.run_id, e.id, getattr(e, "chunk_id", None), text_hash(e.quote), e.source,
                      getattr(e, "path", ""), e.heading, e.url, e.kind, json.dumps(e.sub_questions)) for e in items])

    def section_inputs(self, section: str, ids: list[str], included: int, prompt_chars: int) -> None:
        self._write("INSERT INTO section_inputs (run_id, section, position, eid, included, prompt_chars) VALUES (?,?,?,?,?,?)",
                    [(self.run_id, section, i, eid, int(i <= included), prompt_chars) for i, eid in enumerate(ids, 1)])

    def sentences(self, report_md: str) -> None:
        rows = report_sentences(report_md)
        self._write("DELETE FROM sentences WHERE run_id=?", (self.run_id,))
        self._write("INSERT INTO sentences (run_id, section, position, sentence_key, text, cites, flag) VALUES (?,?,?,?,?,?,?)",
                    [(self.run_id, r["section"], r["position"],
                      hashlib.sha1(f"{self.run_id}|{r['section']}|{r['text']}".encode()).hexdigest()[:16],
                      r["text"], json.dumps(r["cites"]), r["flag"]) for r in rows])


NULL = RunTrace("", "")
CURRENT: contextvars.ContextVar[RunTrace] = contextvars.ContextVar("desk_trace", default=NULL)


def current() -> RunTrace:
    return CURRENT.get()
