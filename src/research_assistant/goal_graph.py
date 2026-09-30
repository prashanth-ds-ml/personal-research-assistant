"""Goal-driven deep research as a LangGraph graph with human-in-the-loop.

  refresh_library -> make_questions -> clarify --(interrupt: questions)--> plan -> approve
        --(interrupt: plan)--> collect (optional) -> research -> write -> save
                          ^_______ revise (feedback) _______|

The run PAUSES at the two interrupts. A client (the dashboard, or a script)
resumes it with ``Command(resume=...)``:

  clarify  -> resume with a string of answers (or "" to skip)
  approve  -> resume with {"approved": true} or {"feedback": "add a section on X"}
              (anything else is refused and asked again; feedback is accepted only while
              revisions are left, and the final plan is always shown for approval)

Everything expensive (evidence extraction, writing) happens only after approval.
"""

import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

import frontmatter
import httpx
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from typing_extensions import TypedDict

from research_assistant import deep_report, fetcher, vault
from research_assistant.configuration import Configuration
from research_assistant.documents import make_embeddings
from research_assistant.knowledge import (
    KnowledgeBase,
    convert_to_markdown,
    default_kb_path,
    folder_namespaces,
)

MAX_PLAN_REVISIONS = 2


class DeepState(TypedDict, total=False):
    goal: str
    questions: list[str]
    clarifications: str
    refined_goal: str
    plan: dict
    plan_notes: str
    library_update: dict
    collect_report: dict
    revisions: int
    evidence: list[dict]
    report: str
    report_path: str
    stats: dict


class DeepInput(TypedDict):
    goal: str


class DeepOutput(TypedDict, total=False):
    report: str
    report_path: str
    stats: dict
    plan: dict


# ---- factories (module-level so tests can substitute fakes) ---------------

def build_llms(cfg: Configuration) -> dict[str, deep_report.LLM]:
    url = cfg.ollama_base_url.rstrip("/")
    return {
        # temperature 0: the same goal should give the same plan (it varied between 5 and 7 sections)
        "planner": deep_report.ollama_llm(cfg.planner_model or cfg.local_llm, url, temperature=0),
        "extractor": deep_report.ollama_llm(cfg.extractor_model or cfg.local_llm, url, temperature=0),
        "writer": deep_report.ollama_llm(cfg.writer_model or cfg.local_llm, url),
    }


def open_kb(cfg: Configuration) -> KnowledgeBase:
    """Open the knowledge base. Use it as a context manager so the connection is closed."""
    path = cfg.kb_path or default_kb_path(cfg.vault_path)
    return KnowledgeBase(path, make_embeddings(cfg.embedding_model, cfg.ollama_base_url),
                         embedding_model=cfg.embedding_model)


def library_folders(cfg: Configuration) -> list[Path]:
    """Configured folders (or <vault>/Sources and <vault>/Library), existing ones only."""
    if cfg.library_folders.strip():
        candidates = [Path(x.strip()) for x in cfg.library_folders.split(";") if x.strip()]
    elif cfg.vault_path:
        candidates = [Path(cfg.vault_path) / "Sources", Path(cfg.vault_path) / "Library"]
    else:
        candidates = []
    return [p for p in candidates if p.is_dir()]


# ---- nodes ----------------------------------------------------------------

def refresh_library(state: DeepState, config: RunnableConfig) -> dict:
    """Index new/changed files in the library folders so a dropped-in PDF is searchable
    without running any script. Unchanged files are skipped by hash, so this is cheap when
    nothing changed. Never fails the run: problems are reported in ``library_update``."""
    cfg = Configuration.from_runnable_config(config)
    folders = library_folders(cfg)
    if not cfg.auto_ingest or not folders:
        return {"library_update": {}}
    try:
        namespaces = folder_namespaces(folders)
        total = {"added": 0, "removed": 0, "empty": 0, "failed": []}
        with open_kb(cfg) as kb:
            for folder in folders:
                stats = kb.ingest_folder(folder, namespace=namespaces[folder.resolve()])
                for key in ("added", "removed", "empty"):
                    total[key] += stats.get(key, 0)
                total["failed"] += stats["failed"]
            total["documents"] = kb.stats()["documents"]
        return {"library_update": total}
    except Exception as e:  # e.g. Ollama (embeddings) down: the run can still use the existing index
        return {"library_update": {"error": str(e)[:300]}}


CLARIFY_PROMPT = """A user wants a deep research report. Goal: {goal}

The report will be built ONLY from a private library of documents on: {library}

Ask up to 4 short clarifying questions whose answers would materially change the research: scope,
audience, depth, region/population, what decision it supports, what to exclude. Do not ask things the goal
already answers. If the goal is already specific enough, return no questions.
Return JSON: {{"questions": [strings]}}"""


def make_questions(state: DeepState, config: RunnableConfig) -> dict:
    """Write the clarifying questions. Kept apart from ``clarify`` on purpose: a node that calls
    ``interrupt`` is re-executed from its first line when the user answers, so putting the model call
    in the same node would repeat it on every resume (and could return different questions, or none,
    throwing away the answers)."""
    cfg = Configuration.from_runnable_config(config)
    if not cfg.ask_clarifying_questions:
        return {"questions": []}
    with open_kb(cfg) as kb:
        titles = ", ".join(r[0] for r in kb.db.execute("SELECT title FROM docs LIMIT 12").fetchall())
    llm = build_llms(cfg)["planner"]
    raw = deep_report._obj(deep_report._json(
        llm(CLARIFY_PROMPT.format(goal=state["goal"], library=titles or "(empty)"), json_mode=True), {}))
    asked = raw.get("questions")
    questions = [q.strip() for q in asked if isinstance(q, str) and q.strip()][:4] if isinstance(asked, list) else []
    return {"questions": questions}


def clarify(state: DeepState, config: RunnableConfig) -> dict:
    goal = state["goal"]
    questions = state.get("questions") or []
    if not questions:
        return {"refined_goal": goal, "revisions": 0}

    answers = interrupt({"type": "clarify", "goal": goal, "questions": questions})
    text = answers if isinstance(answers, str) else "\n".join(f"{k}: {v}" for k, v in (answers or {}).items())
    text = text.strip()
    refined = goal if not text else f"{goal}\n\nClarifications from the user:\n{text}"
    return {"clarifications": text, "refined_goal": refined, "revisions": 0}


def plan(state: DeepState, config: RunnableConfig) -> dict:
    cfg = Configuration.from_runnable_config(config)
    lessons = ""
    if cfg.vault_path:
        lessons = deep_report.format_lessons(vault.recent_feedback(cfg.vault_path, cfg.research_subdir, 5))
    p = deep_report.make_plan(state.get("refined_goal") or state["goal"], build_llms(cfg)["planner"],
                              notes=state.get("plan_notes", ""), lessons=lessons)
    return {"plan": {"goal": p.goal, "title": p.title, "sub_questions": p.sub_questions, "outline": p.outline}}


def _valid_decision(decision: Any, revisions_left: int) -> bool:
    if not isinstance(decision, dict):
        return False
    return bool(decision.get("approved")) or bool(decision.get("feedback") and revisions_left > 0)


def approve(state: DeepState, config: RunnableConfig) -> dict:
    """Show the plan and wait. Approval is explicit ({"approved": true}); feedback asks for a revision
    while revisions remain. The LAST plan is shown too (with revisions_left 0, approve-only), so no plan
    ever runs unseen. Anything else is refused and asked again once."""
    cfg = Configuration.from_runnable_config(config)
    if not cfg.require_plan_approval:
        return {"plan_notes": ""}
    revisions = state.get("revisions", 0)
    left = max(MAX_PLAN_REVISIONS - revisions, 0)
    payload = {"type": "approve_plan", "plan": state["plan"], "revisions_left": left}
    decision = interrupt(payload)
    if not _valid_decision(decision, left):
        hint = 'Reply {"approved": true}' + (' or {"feedback": "..."}' if left else " (no revisions are left)")
        decision = interrupt({**payload, "error": f"Not understood. {hint}."})
    if isinstance(decision, dict) and decision.get("feedback") and left > 0 and not decision.get("approved"):
        return {"plan_notes": str(decision["feedback"]), "revisions": revisions + 1}
    if isinstance(decision, dict) and decision.get("approved"):
        return {"plan_notes": ""}
    raise RuntimeError("The plan was not approved, so the run was stopped before any evidence was gathered.")


def route_after_approval(state: DeepState) -> str:
    return "plan" if state.get("plan_notes") else "research"


def _pdf_to_markdown(raw: bytes, name: str) -> str:
    """Downloaded PDF bytes -> markdown via the same converter the ingest uses (Docling, OCR off)."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"{name[:60]}.pdf"
        path.write_bytes(raw)
        return convert_to_markdown(path)


def collect(state: DeepState, config: RunnableConfig) -> dict:
    """Optional step after plan approval: fetch open-access papers for the plan's questions (and any
    seed URLs) into <vault>/Library, then index them so this very run can cite them. Never fails the
    run; everything it did or skipped is in the manifest, and what was really indexed is reported."""
    cfg = Configuration.from_runnable_config(config)
    seeds = [u for u in re.split(r"[\s;]+", cfg.seed_urls) if u.startswith(("http://", "https://"))]
    if not (cfg.collect_sources or seeds) or not cfg.vault_path:
        return {}
    try:
        library = Path(cfg.vault_path) / "Library"
        library.mkdir(parents=True, exist_ok=True)
        plan_ = state["plan"]
        store = fetcher.SourceStore(library, f"{date.today().isoformat()}-{vault.slugify(plan_['title'])}")
        with httpx.Client() as http:
            fx = fetcher.Fetcher(http=http, contact=cfg.contact_email)
            summary = fetcher.collect(
                plan_["sub_questions"] if cfg.collect_sources else [], store, fx, build_llms(cfg)["planner"],
                seeds=seeds, max_sources=cfg.fetch_max_sources, keep_score=cfg.fetch_min_relevance,
                convert_pdf=_pdf_to_markdown)
        if summary["saved"]:
            namespaces = folder_namespaces([*library_folders(cfg), library])       # same key the auto-ingest uses
            with open_kb(cfg) as kb:                                             # index now, so research can use them
                ing = kb.ingest_folder(library, namespace=namespaces[library.resolve()])
            summary["indexed"] = ing["added"]
            if ing["failed"]:
                summary["index_failed"] = ing["failed"][:5]
            if ing["added"] < summary["saved"]:
                summary["warning"] = (f"{summary['saved']} sources were saved but only {ing['added']} were indexed, "
                                      "so this run may not see all of them.")
        return {"collect_report": summary}
    except Exception as e:
        return {"collect_report": {"error": str(e)[:300]}}


def _plan_obj(d: dict) -> deep_report.Plan:
    return deep_report.Plan(goal=d["goal"], title=d["title"], sub_questions=d["sub_questions"], outline=d["outline"])


def research(state: DeepState, config: RunnableConfig) -> dict:
    cfg = Configuration.from_runnable_config(config)
    llms = build_llms(cfg)
    deep_report.reset_stats()
    with open_kb(cfg) as kb:
        ev = deep_report.gather_evidence(
            _plan_obj(state["plan"]), lambda q: kb.search(q, k=6), llms["extractor"],
            query_llm=llms["planner"], k=cfg.docs_retrieval_k)
    deep_report.check_model_health(deep_report.snapshot_stats(), len(ev))   # raises if the model was down
    return {"evidence": [e.__dict__ for e in ev]}


def _scope_note(collect_report: dict | None) -> str:
    """What else was searched this run, for the report's Limitations (empty = library only)."""
    if not collect_report or collect_report.get("error"):
        return ""
    saved = collect_report.get("saved", 0)
    if saved:
        return (f"{saved} new source(s) were fetched for this run from arXiv, Europe PMC and/or URLs you supplied "
                f"({collect_report.get('skipped', 0)} candidates skipped) and added to the library.")
    return "Fetching new sources was switched on but found nothing new worth keeping."


def write(state: DeepState, config: RunnableConfig) -> dict:
    cfg = Configuration.from_runnable_config(config)
    llm = build_llms(cfg)["writer"]
    plan_ = _plan_obj(state["plan"])
    evidence = [deep_report.Evidence(**e) for e in state["evidence"]]
    sections = deep_report.write_all(plan_, evidence, llm)
    llm_stats = deep_report.snapshot_stats()
    notes = []
    if llm_stats["gave_up"]:
        notes.append(f"The model failed to answer {llm_stats['gave_up']} of {llm_stats['calls']} requests during this "
                     "run, so some parts may be thinner than the evidence allows.")
    with open_kb(cfg) as kb:
        library_size = kb.stats()["documents"]
    report = deep_report.assemble(plan_, sections, evidence, llm, library_size=library_size, notes=notes,
                                  scope_note=_scope_note(state.get("collect_report")))
    return {"report": report, "stats": {
        "questions": len(plan_.sub_questions), "sections": len(sections),
        "evidence": len(evidence), "words": len(report.split()),
        "sources": len({e.source for e in evidence}),
        **{f"llm_{k}": v for k, v in llm_stats.items()}}}


def save(state: DeepState, config: RunnableConfig) -> dict:
    cfg = Configuration.from_runnable_config(config)
    if not cfg.vault_path:
        return {}
    research_dir = Path(cfg.vault_path) / cfg.research_subdir
    research_dir.mkdir(parents=True, exist_ok=True)
    base = f"{date.today().isoformat()}-{vault.slugify(state['plan']['title'])}"
    post = frontmatter.Post(
        state["report"], title=state["plan"]["title"], date=date.today().isoformat(), kind="deep-research",
        goal=state["goal"], clarifications=state.get("clarifications", ""), status="complete",
        loops=state["stats"]["questions"], sources_count=state["stats"].get("sources", 0), **state["stats"])
    text = frontmatter.dumps(post)
    n = 1
    while True:
        path = research_dir / (f"{base}.md" if n == 1 else f"{base}-{n}.md")
        try:
            with open(path, "x", encoding="utf-8") as fh:        # exclusive: never overwrite another run's report
                fh.write(text)
            return {"report_path": str(path)}
        except FileExistsError:
            n += 1


def _graph(checkpointer: Any = None) -> Any:
    b = StateGraph(DeepState, input_schema=DeepInput, output_schema=DeepOutput)
    for name, fn in [("refresh_library", refresh_library), ("make_questions", make_questions), ("clarify", clarify),
                     ("plan", plan), ("approve", approve), ("collect", collect), ("research", research),
                     ("write", write), ("save", save)]:
        b.add_node(name, fn)
    b.add_edge(START, "refresh_library")
    b.add_edge("refresh_library", "make_questions")
    b.add_edge("make_questions", "clarify")
    b.add_edge("clarify", "plan")
    b.add_edge("plan", "approve")
    b.add_conditional_edges("approve", route_after_approval, {"plan": "plan", "research": "collect"})
    b.add_edge("collect", "research")
    b.add_edge("research", "write")
    b.add_edge("write", "save")
    b.add_edge("save", END)
    return b.compile(checkpointer=checkpointer)


graph = _graph()
