"""A small on-disk record of every deep-research run: what it is doing now, what it did, how it ended.

One JSON file per run at ``<vault>/.runs/<run_id>.json`` (run id = the LangGraph thread id). The graph's nodes
update it as they go, and the dashboard reads it for the run history and the live progress view. It lives in the
vault, not in LangGraph's in-memory store, so it survives a backend restart: a run whose server died still shows up,
with what it had finished.

Writes never raise: a full disk or a locked file must not stop a research run, so every mutation swallows OSError.
Each mutation is read-modify-write under one lock and replaces the file atomically, so a reader never sees half a file.
"""

import json
import os
import re
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

RUNS_DIR = ".runs"
MAX_EVENTS = 400
_LOCK = threading.Lock()
_ID_RE = re.compile(r"^[\w.-]{1,80}$")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def valid_id(run_id: str) -> bool:
    return bool(_ID_RE.match(run_id or "")) and ".." not in run_id


class RunLog:
    """Handle for one run's record. With no vault or no run id it is a silent no-op (tests, scripts)."""

    def __init__(self, vault_path: str, run_id: str):
        self.enabled = bool(vault_path) and valid_id(run_id)
        self.run_id = run_id
        self.dir = Path(vault_path) / RUNS_DIR if vault_path else None

    @property
    def path(self) -> Path | None:
        return self.dir / f"{self.run_id}.json" if self.enabled and self.dir else None

    # ---- reading / writing ------------------------------------------------

    def _read(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def _load(self) -> dict | None:
        """The record for a write: None when there is none yet or its contents are corrupt (start afresh). A read that FAILS
        (OSError, for example a sharing violation while the dashboard has the file open) raises, so the write is skipped
        instead of replacing the history with an empty record."""
        try:
            text = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None
        try:
            data = json.loads(text)
        except ValueError:
            return None
        return data if isinstance(data, dict) else None

    def _mutate(self, fn) -> None:
        if not self.enabled:
            return
        with _LOCK:
            try:
                self.dir.mkdir(parents=True, exist_ok=True)
                data = self._load() or {"id": self.run_id, "status": "running", "started_at": _now(),
                                        "progress": {}, "events": []}
                fn(data)
                data["updated_at"] = _now()
                tmp = self.path.with_suffix(".tmp")
                tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
                for attempt in range(4):                      # Windows: the dashboard may be reading the file this instant
                    try:
                        os.replace(tmp, self.path)
                        break
                    except PermissionError:
                        if attempt == 3:
                            raise
                        time.sleep(0.05)
            except (OSError, ValueError, TypeError):
                pass                                                 # never let bookkeeping break a run

    def is_stopped(self) -> bool:
        """True once the user pressed Stop (the dashboard writes status "stopped"). Cheap: one small file read."""
        return self.enabled and self._read().get("status") == "stopped"

    # ---- what the graph reports -------------------------------------------

    def start(self, goal: str, **settings) -> None:
        def f(d):
            d.setdefault("goal", goal)
            d["settings"] = {**d.get("settings", {}), **settings}
        self._mutate(f)

    def step(self, name: str, text: str = "") -> None:
        """Entering a pipeline step (status goes back to running)."""
        def f(d):
            d["step"], d["waiting_for"] = name, None
            if d.get("status") != "stopped":              # a Stop pressed between steps must survive the next step
                d["status"] = "running"
            if text:
                _add_event(d, text)
        self._mutate(f)

    def event(self, text: str, **data) -> None:
        self._mutate(lambda d: _add_event(d, text, **data))

    def progress(self, **fields) -> None:
        """Counters for the live view (questions_done, evidence, sections_done, current ...)."""
        self._mutate(lambda d: d.setdefault("progress", {}).update(fields))

    def record(self, **fields) -> None:
        """Top-level facts about the run for the dashboard (for example the sources collected or used)."""
        self._mutate(lambda d: d.update(fields))

    def waiting(self, kind: str) -> None:
        """Paused for the user: kind is 'clarify', 'approve' or 'review'."""
        def f(d):
            d["status"], d["waiting_for"] = "waiting", kind
        self._mutate(f)

    def finish(self, report_path: str = "", stats: dict | None = None) -> None:
        def f(d):
            d.update(status="done", step="done", waiting_for=None, report_path=report_path, stats=stats or {})
            _add_event(d, "Report saved")
        self._mutate(f)

    def fail(self, error: str) -> None:
        def f(d):
            d.update(status="failed", waiting_for=None, error=error[:500])
            _add_event(d, f"Failed: {error[:200]}", level="error")
        self._mutate(f)

    # ---- partial evidence, so a retry does not redo finished questions ------

    @property
    def partial_path(self) -> Path | None:
        return self.dir / f"{self.run_id}.evidence.json" if self.enabled and self.dir else None

    def save_partial(self, questions_done: int, evidence: list[dict]) -> None:
        if not self.enabled:
            return
        with _LOCK:
            try:
                self.dir.mkdir(parents=True, exist_ok=True)
                tmp = self.partial_path.with_suffix(".tmp")
                tmp.write_text(json.dumps({"questions_done": questions_done, "evidence": evidence}), encoding="utf-8")
                os.replace(tmp, self.partial_path)
            except (OSError, ValueError, TypeError):
                pass

    def load_partial(self) -> tuple[int, list[dict]]:
        if not self.enabled:
            return 0, []
        try:
            data = json.loads(self.partial_path.read_text(encoding="utf-8"))
            done, ev = int(data["questions_done"]), data["evidence"]
            return (done, ev) if isinstance(ev, list) and done >= 0 else (0, [])
        except (OSError, ValueError, KeyError, TypeError):
            return 0, []

    def clear_partial(self) -> None:
        if self.enabled:
            try:
                self.partial_path.unlink(missing_ok=True)
            except OSError:
                pass


def _add_event(d: dict, text: str, **data) -> None:
    events = d.setdefault("events", [])
    events.append({"t": _now(), "text": text[:300], **data})
    if len(events) > MAX_EVENTS:
        del events[: len(events) - MAX_EVENTS]


# ---- reading runs (history) -------------------------------------------------

def read_run(vault_path: str, run_id: str) -> dict | None:
    log = RunLog(vault_path, run_id)
    return log._read() or None if log.enabled else None


def list_runs(vault_path: str) -> list[dict]:
    """Every run, newest first, without the event lists (those are loaded per run)."""
    runs_dir = Path(vault_path) / RUNS_DIR if vault_path else None
    if not runs_dir or not runs_dir.is_dir():
        return []
    out = []
    for f in runs_dir.glob("*.json"):
        if f.name.endswith(".evidence.json"):
            continue
        run = read_run(vault_path, f.stem)
        if run:
            out.append({k: v for k, v in run.items() if k != "events"})
    return sorted(out, key=lambda r: r.get("updated_at", ""), reverse=True)
