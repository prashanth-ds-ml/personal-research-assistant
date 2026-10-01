"""Goal-driven deep research as a LangGraph graph with human-in-the-loop.

  refresh_library -> make_questions -> clarify --(interrupt: questions)--> plan -> approve
        --(interrupt: plan)--> discover -> review --(interrupt: sources)--> collect -> research -> write -> save
                          ^_______ revise (feedback) _______|

The run PAUSES at the two interrupts. A client (the dashboard, or a script)
resumes it with ``Command(resume=...)``:

  clarify  -> resume with a string of answers (or "" to skip)
  review   -> resume with {"selected": [candidate ids]} (only when "Fetch new sources" is on and candidates exist)
  approve  -> resume with {"approved": true} or {"feedback": "add a section on X"}
              (anything else is refused and asked again; feedback is accepted only while
              revisions are left, and the final plan is always shown for approval)

Everything expensive (evidence extraction, writing) happens only after approval.
"""

import functools
import re
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

import frontmatter
import httpx
from langchain_core.runnables import RunnableConfig
from langgraph.errors import GraphBubbleUp
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from typing_extensions import TypedDict

from research_assistant import collector, deep_report, fetcher, runlog, vault
from research_assistant.configuration import PER_RUN_KEYS, Configuration
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
    options: dict
    candidates: list[dict]
    selected_ids: list[str]
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


def library_search(kb: KnowledgeBase, cfg: Configuration, k: int = 6):
    """The search function deep research uses. The quick assistant archives what it found into Sources/. Real web pages
    there are good evidence, but copies of your own local documents (doc:// pages) are not web sources and only repeat
    files already in the library, so those are left out unless the user asked for them."""
    prefix = f"{cfg.sources_subdir}/"

    def skip(path: str, source_kind: str) -> bool:
        return not cfg.include_archived_pages and path.startswith(prefix) and source_kind in ("document", "")

    return lambda q: kb.search(q, k=k, skip=skip)


def library_folders(cfg: Configuration) -> list[Path]:
    """Configured folders (or <vault>/Sources and <vault>/Library), existing ones only."""
    if cfg.library_folders.strip():
        candidates = [Path(x.strip()) for x in cfg.library_folders.split(";") if x.strip()]
    elif cfg.vault_path:
        candidates = [Path(cfg.vault_path) / "Sources", Path(cfg.vault_path) / "Library"]
    else:
        candidates = []
    return [p for p in candidates if p.is_dir()]


# ---- run record -------------------------------------------------------------

def _run_log(config: RunnableConfig) -> runlog.RunLog:
    """The on-disk record for this run (see runlog.py); a silent no-op without a vault or thread id."""
    cfg = Configuration.from_runnable_config(config)
    return runlog.RunLog(cfg.vault_path, str((config.get("configurable") or {}).get("thread_id", "")))


def _cfg(state: DeepState, config: RunnableConfig) -> Configuration:
    """Settings for a node. The dashboard sends the per-run options (collect sources, seed URLs ...) only with the
    call that starts the run; each later resume carries none. They are saved in the run's state at the start
    (``options``), and the current call's own values still win."""
    saved = state.get("options") or {}
    current = dict(config.get("configurable") or {})
    return Configuration.from_runnable_config({**config, "configurable": {**saved, **current}})


def _opts(config: RunnableConfig) -> dict:
    """The per-run options of the starting call, to be stored in the state."""
    return {"options": {k: v for k, v in (config.get("configurable") or {}).items() if k in PER_RUN_KEYS}}


def tracked(step: str, label: str = ""):
    """Record that a node started, and that it failed if it raised. A pause for the user (GraphBubbleUp) is not a
    failure and passes through untouched."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(state: DeepState, config: RunnableConfig):
            log = _run_log(config)
            log.start(state.get("goal", ""))
            log.step(step, label)
            deep_report.set_stop_check(log.is_stopped if log.enabled else None)   # lets Stop reach a running model call
            try:
                return fn(state, config)
            except (GraphBubbleUp, deep_report.RunStopped):      # a pause for the user, or the user's own Stop
                raise
            except Exception as e:
                log.fail(f"{step}: {e}")
                raise
        return wrapper
    return deco


# ---- nodes ----------------------------------------------------------------

@tracked("library", "Checking the library for new files")
def refresh_library(state: DeepState, config: RunnableConfig) -> dict:
    """Index new/changed files in the library folders so a dropped-in PDF is searchable
    without running any script. Unchanged files are skipped by hash, so this is cheap when
    nothing changed. Never fails the run: problems are reported in ``library_update``."""
    cfg = _cfg(state, config)
    folders = library_folders(cfg)
    if not cfg.auto_ingest or not folders:
        return {"library_update": {}, **_opts(config)}
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
        _run_log(config).event(f"Library: {total['documents']} documents ({total['added']} new)")
        return {"library_update": total, **_opts(config)}
    except Exception as e:  # e.g. Ollama (embeddings) down: the run can still use the existing index
        return {"library_update": {"error": str(e)[:300]}, **_opts(config)}


CLARIFY_PROMPT = """A user wants a deep research report. Goal: {goal}

The report will be built ONLY from a private library of documents on: {library}

Ask up to 4 short clarifying questions whose answers would materially change the research: scope,
audience, depth, region/population, what decision it supports, what to exclude. Do not ask things the goal
already answers. If the goal is already specific enough, return no questions.
Return JSON: {{"questions": [strings]}}"""


@tracked("questions", "Writing clarifying questions")
def make_questions(state: DeepState, config: RunnableConfig) -> dict:
    """Write the clarifying questions. Kept apart from ``clarify`` on purpose: a node that calls
    ``interrupt`` is re-executed from its first line when the user answers, so putting the model call
    in the same node would repeat it on every resume (and could return different questions, or none,
    throwing away the answers)."""
    cfg = _cfg(state, config)
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


@tracked("clarify")
def clarify(state: DeepState, config: RunnableConfig) -> dict:
    goal = state["goal"]
    questions = state.get("questions") or []
    if not questions:
        return {"refined_goal": goal, "revisions": 0}

    _run_log(config).waiting("clarify")
    answers = interrupt({"type": "clarify", "goal": goal, "questions": questions})
    text = answers if isinstance(answers, str) else "\n".join(f"{k}: {v}" for k, v in (answers or {}).items())
    text = text.strip()
    refined = goal if not text else f"{goal}\n\nClarifications from the user:\n{text}"
    return {"clarifications": text, "refined_goal": refined, "revisions": 0}


@tracked("plan", "Planning the research")
def plan(state: DeepState, config: RunnableConfig) -> dict:
    cfg = _cfg(state, config)
    lessons = ""
    if cfg.vault_path:
        lessons = deep_report.format_lessons(vault.recent_feedback(cfg.vault_path, cfg.research_subdir, 5))
    p = deep_report.make_plan(state.get("refined_goal") or state["goal"], build_llms(cfg)["planner"],
                              notes=state.get("plan_notes", ""), lessons=lessons)
    _run_log(config).event(f"Plan: {len(p.sub_questions)} questions, {len(p.outline)} sections")
    return {"plan": {"goal": p.goal, "title": p.title, "sub_questions": p.sub_questions, "outline": p.outline}}


def _valid_decision(decision: Any, revisions_left: int) -> bool:
    if not isinstance(decision, dict):
        return False
    return bool(decision.get("approved")) or bool(decision.get("feedback") and revisions_left > 0)


@tracked("approve")
def approve(state: DeepState, config: RunnableConfig) -> dict:
    """Show the plan and wait. Approval is explicit ({"approved": true}); feedback asks for a revision
    while revisions remain. The LAST plan is shown too (with revisions_left 0, approve-only), so no plan
    ever runs unseen. Anything else is refused and asked again once."""
    cfg = _cfg(state, config)
    if not cfg.require_plan_approval:
        return {"plan_notes": ""}
    revisions = state.get("revisions", 0)
    left = max(MAX_PLAN_REVISIONS - revisions, 0)
    payload = {"type": "approve_plan", "plan": state["plan"], "revisions_left": left}
    _run_log(config).waiting("approve")
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


def _source_store(cfg: Configuration, plan_: dict) -> tuple[Path, fetcher.SourceStore]:
    library = Path(cfg.vault_path) / "Library"
    library.mkdir(parents=True, exist_ok=True)
    return library, fetcher.SourceStore(library, f"{date.today().isoformat()}-{vault.slugify(plan_['title'])}")


@tracked("discover", "Looking for sources")
def discover(state: DeepState, config: RunnableConfig) -> dict:
    """With "Fetch new sources" on: search the web and the open-access paper APIs for each plan question, one question
    after another, and judge each result. Downloads nothing; the user chooses in the next step. Never fails the run."""
    cfg = _cfg(state, config)
    if not cfg.collect_sources or not cfg.vault_path:
        return {"candidates": [], "selected_ids": []}
    log = _run_log(config)
    try:
        _, store = _source_store(cfg, state["plan"])
        with httpx.Client() as http:
            fx = fetcher.Fetcher(http=http, contact=cfg.contact_email)
            found = collector.discover(
                state["plan"]["sub_questions"], search=collector.make_search(cfg.search_backend, cfg.searxng_url, http),
                fx=fx, store=store, llm=build_llms(cfg)["planner"], per_question=cfg.collect_candidates_per_question,
                allow=collector.split_domains(cfg.collect_allow_domains),
                block=collector.split_domains(cfg.collect_block_domains), on_progress=log.event)
        log.event(f"Found {len(found)} candidate sources")
        return {"candidates": found, "selected_ids": []}
    except Exception as e:
        log.event(f"Source search failed: {str(e)[:150]}", level="error")
        return {"candidates": [], "selected_ids": [], "collect_report": {"error": str(e)[:300]}}


def _valid_selection(decision: Any) -> bool:
    return isinstance(decision, dict) and isinstance(decision.get("selected"), list)


@tracked("review")
def review(state: DeepState, config: RunnableConfig) -> dict:
    """Show the candidates and wait for the user's choice. With reviewing switched off, take everything scoring at least
    the minimum relevance. An unreadable answer is asked for once more, then treated as "collect nothing"."""
    cfg = _cfg(state, config)
    cands = state.get("candidates") or []
    if not cands:
        return {"selected_ids": []}
    if not cfg.collect_review:
        return {"selected_ids": [d["id"] for d in cands if d["score"] >= cfg.fetch_min_relevance]}
    payload = {"type": "review_sources", "candidates": cands, "max_sources": cfg.fetch_max_sources,
               "min_relevance": cfg.fetch_min_relevance}
    _run_log(config).waiting("review")
    decision = interrupt(payload)
    if not _valid_selection(decision):
        decision = interrupt({**payload, "error": 'Not understood. Reply {"selected": [ids]} (an empty list skips fetching).'})
    if not _valid_selection(decision):
        return {"selected_ids": []}
    known = {d["id"] for d in cands}
    chosen = [i for i in decision["selected"] if isinstance(i, str) and i in known]
    return {"selected_ids": list(dict.fromkeys(chosen))}


@tracked("collect", "Collecting the chosen sources")
def collect(state: DeepState, config: RunnableConfig) -> dict:
    """Fetch the seed URLs and the sources the user chose, one at a time, into <vault>/Library, then index them so
    this very run can cite them. Never fails the run; everything done or skipped is in the manifest."""
    cfg = _cfg(state, config)
    log = _run_log(config)
    seeds = [u for u in re.split(r"[\s;]+", cfg.seed_urls) if u.startswith(("http://", "https://"))]
    by_id = {d["id"]: d for d in state.get("candidates") or []}
    picked = [by_id[i] for i in state.get("selected_ids") or [] if i in by_id]
    if not (picked or seeds) or not cfg.vault_path:
        return {}
    try:
        library, store = _source_store(cfg, state["plan"])
        todo = [fetcher.Candidate(source="seed", id=fetcher.slugify(u), title=u, url=u, page_url=u,
                                  licence="user-supplied URL; private use") for u in seeds]
        todo += [collector.from_dict(d) for d in picked]
        with httpx.Client() as http:
            fx = fetcher.Fetcher(http=http, contact=cfg.contact_email)
            summary = collector.collect_selected(todo, store, fx, convert_pdf=_pdf_to_markdown,
                                                 max_sources=cfg.fetch_max_sources, on_progress=log.event)
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
        log.event(f"Collected {summary['saved']} sources ({summary['skipped']} skipped, {summary['failed']} failed)")
        log.record(collected=[_collected_row(m) for m in store.manifest])
        return {"collect_report": summary}
    except Exception as e:
        log.event(f"Collecting sources failed: {str(e)[:150]}", level="error")
        return {"collect_report": {"error": str(e)[:300]}}


def _collected_row(m: dict) -> dict:
    """One line of the collect manifest, as the dashboard shows it: what it is, where it came from, what happened."""
    url = m.get("url", "")
    kind = ("pdf" if m.get("source") == "arxiv" or url.lower().split("?")[0].endswith(".pdf")
            else "paper" if m.get("source") == "europepmc" else "web")
    return {"title": m.get("title", ""), "url": url, "kind": kind, "status": m.get("status", ""),
            "reason": m.get("reason", "")}


def _plan_obj(d: dict) -> deep_report.Plan:
    return deep_report.Plan(goal=d["goal"], title=d["title"], sub_questions=d["sub_questions"], outline=d["outline"])


@tracked("research", "Extracting evidence from the library")
def research(state: DeepState, config: RunnableConfig) -> dict:
    cfg = _cfg(state, config)
    llms = build_llms(cfg)
    log = _run_log(config)
    plan_ = _plan_obj(state["plan"])
    deep_report.reset_stats()
    # A retry after a failure continues from the questions already finished instead of starting over.
    done0, saved = log.load_partial()
    resume = (done0, [deep_report.Evidence(**e) for e in saved]) if done0 else None
    log.progress(questions_total=len(plan_.sub_questions), questions_done=done0, evidence=len(saved), current="")
    if done0:
        log.event(f"Resuming after question {done0} ({len(saved)} facts already kept)")

    def question_done(done: int, total: int, ev: list) -> None:
        log.progress(questions_done=done, questions_total=total, evidence=len(ev))
        log.save_partial(done, [e.__dict__ for e in ev])

    def note(message: str) -> None:
        log.event(message)
        log.progress(current=message)

    with open_kb(cfg) as kb:
        ev = deep_report.gather_evidence(
            plan_, library_search(kb, cfg), llms["extractor"], on_progress=note,
            query_llm=llms["planner"], k=cfg.docs_retrieval_k, resume=resume, on_question_done=question_done)
    deep_report.check_model_health(deep_report.snapshot_stats(), len(ev))   # raises if the model was down
    dropped = deep_report.snapshot_stats()["off_topic"]
    if dropped:
        log.event(f"Left out {dropped} fact(s) that were true but not about the question")
    log.progress(off_topic=dropped)
    log.clear_partial()
    return {"evidence": [e.__dict__ for e in ev]}


def _scope_note(collect_report: dict | None) -> str:
    """What else was searched this run, for the report's Limitations (empty = library only)."""
    if not collect_report or collect_report.get("error"):
        return ""
    saved = collect_report.get("saved", 0)
    if saved:
        pages, papers = collect_report.get("pages"), collect_report.get("papers")
        mix = f" ({pages} web page(s), {papers} paper(s))" if pages is not None and papers is not None else ""
        return (f"{saved} new source(s){mix} were collected for this run, chosen by the user from web search, arXiv, "
                f"Europe PMC and/or URLs supplied, and added to the library; {collect_report.get('skipped', 0)} candidates "
                "were skipped. Web pages are less reliable than papers: check the cited quotes.")
    return "Fetching new sources was switched on but found nothing new worth keeping."


@tracked("write", "Writing the report")
def write(state: DeepState, config: RunnableConfig) -> dict:
    cfg = _cfg(state, config)
    llm = build_llms(cfg)["writer"]
    log = _run_log(config)
    plan_ = _plan_obj(state["plan"])
    evidence = [deep_report.Evidence(**e) for e in state["evidence"]]
    written = [0]

    def section_started(message: str) -> None:
        log.progress(sections_total=len(plan_.outline), sections_done=written[0], current=message)
        log.event(message)
        written[0] += 1

    sections = deep_report.write_all(plan_, evidence, llm, on_progress=section_started)
    log.progress(sections_total=len(plan_.outline), sections_done=len(sections), current="Assembling the report")
    llm_stats = deep_report.snapshot_stats()
    notes = []
    if llm_stats["gave_up"]:
        notes.append(f"The model failed to answer {llm_stats['gave_up']} of {llm_stats['calls']} requests during this "
                     "run, so some parts may be thinner than the evidence allows.")
    with open_kb(cfg) as kb:
        library_size = kb.stats()["documents"]
    report = deep_report.assemble(plan_, sections, evidence, llm, library_size=library_size, notes=notes,
                                  scope_note=_scope_note(state.get("collect_report")))
    cited = {int(n) for n in re.findall(r"\[E(\d+)\]", report.split("## Evidence appendix")[0])}
    groups = deep_report.group_sources(evidence, cited)
    log.record(sources=[{"group": label, **d} for label, items in groups for d in items])
    return {"report": report, "stats": {
        "questions": len(plan_.sub_questions), "sections": len(sections),
        "evidence": len(evidence), "words": len(report.split()),
        "sources": len({e.source for e in evidence}),
        "sources_pdf": sum(len(items) for label, items in groups if label.startswith("Papers")),
        "sources_web": sum(len(items) for label, items in groups if label == "Web pages"),
        **{f"llm_{k}": v for k, v in llm_stats.items()}}}


@tracked("save", "Saving the report")
def save(state: DeepState, config: RunnableConfig) -> dict:
    cfg = _cfg(state, config)
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
            _run_log(config).finish(str(path), state["stats"])
            return {"report_path": str(path)}
        except FileExistsError:
            n += 1


def _graph(checkpointer: Any = None) -> Any:
    b = StateGraph(DeepState, input_schema=DeepInput, output_schema=DeepOutput)
    for name, fn in [("refresh_library", refresh_library), ("make_questions", make_questions), ("clarify", clarify),
                     ("plan", plan), ("approve", approve), ("discover", discover), ("review", review),
                     ("collect", collect), ("research", research),
                     ("write", write), ("save", save)]:
        b.add_node(name, fn)
    b.add_edge(START, "refresh_library")
    b.add_edge("refresh_library", "make_questions")
    b.add_edge("make_questions", "clarify")
    b.add_edge("clarify", "plan")
    b.add_edge("plan", "approve")
    b.add_conditional_edges("approve", route_after_approval, {"plan": "plan", "research": "discover"})
    b.add_edge("discover", "review")
    b.add_edge("review", "collect")
    b.add_edge("collect", "research")
    b.add_edge("research", "write")
    b.add_edge("write", "save")
    b.add_edge("save", END)
    return b.compile(checkpointer=checkpointer)


graph = _graph()
