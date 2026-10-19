"""Deterministic checks on what a report says: is a section backed by enough evidence, is a paragraph a repeat, is a number
from the sources, how well supported is a sentence. Plain code, no model calls, so they are cheap, repeatable and testable.

Used by deep_report.write_all / assemble. ``evidence`` items need the attributes id, claim, quote, source, sub_questions.
"""

import re
from dataclasses import dataclass

# What a section needs before it is written from evidence. Below this it becomes a short, honest gap note.
MIN_FACTS = 3
MIN_DOCS = 2
MIN_SUPPORTED_SHARE = 0.5          # under this share of supported evidence sections the report is a gap report


@dataclass
class Standards:
    min_facts: int = MIN_FACTS
    min_docs: int = MIN_DOCS
    min_share: float = MIN_SUPPORTED_SHARE
    claim_labels: bool = True
    flags_only: bool = False          # v3: tag only sentences that fail a check (or cite nothing), not every sentence


# Text this module writes itself (never labelled or rewritten by later passes).
GENERATED_MARKERS = ("*The library does not have enough evidence", "*This report cannot give a recommendation",
                     "*The model failed to write", "*No findings were available", "*No supporting evidence")
FAILED_MARKER = "*The model failed to write"


def is_generated(body: str) -> bool:
    return body.lstrip().startswith(GENERATED_MARKERS)


# ---- how well is each section supported ----------------------------------------------------------------

def section_support(section: dict, evidence: list, standards: Standards) -> dict:
    """Facts and distinct documents behind one evidence section. Status: supported (enough of both), thin (some evidence,
    not enough) or gap (none)."""
    wanted = set(section.get("questions", []))
    facts = [e for e in evidence if wanted & set(e.sub_questions)]
    docs = {e.source for e in facts}
    if len(facts) >= standards.min_facts and len(docs) >= standards.min_docs:
        status = "supported"
    else:
        status = "thin" if facts else "gap"
    return {"title": section["title"], "facts": len(facts), "documents": len(docs), "status": status,
            "questions": list(section.get("questions", []))}


def plan_support(outline: list[dict], evidence: list, standards: Standards) -> dict[int, dict]:
    """Support for every evidence section (synthesis sections are left out), keyed by position in the outline."""
    return {i: section_support(s, evidence, standards) for i, s in enumerate(outline) if not s.get("synthesis")}


def is_gap_report(supports, standards: Standards) -> bool:
    """True when too few evidence sections are supported for a recommendation to mean anything."""
    items = list(supports)
    return bool(items) and sum(s["status"] == "supported" for s in items) / len(items) < standards.min_share


def mark_failed(supports: dict, sections: list[tuple[str, str]], outline: list[dict]) -> list[str]:
    """Sections whose text is the "model failed to write" note: their status becomes "failed" (the evidence existed, the
    writing did not). Returns their titles."""
    failed = []
    for i, (title, body) in enumerate(sections):
        if i in supports and body.lstrip().startswith(FAILED_MARKER):
            supports[i]["status"] = "failed"
            failed.append(title)
    return failed


def status_table(supports: list[dict], standards: Standards) -> str:
    rows = ["| Section | Facts | Documents | Status |", "|---|---|---|---|"]
    for s in supports:
        label = ("supported" if s["status"] == "supported"
                 else "writing failed (the facts are in the appendix)" if s["status"] == "failed"
                 else f"thin (needs {standards.min_facts} facts from {standards.min_docs} documents)" if s["status"] == "thin"
                 else "no evidence found")
        rows.append(f"| {s['title']} | {s['facts']} | {s['documents']} | {label} |")
    return "\n".join(rows)


def gap_note(section: dict, support: dict, questions: list[str], evidence: list, standards: Standards) -> str:
    """The text of a section the evidence cannot carry: what is missing, what little there is, what to collect."""
    wanted = set(section.get("questions", []))
    own = [e for e in evidence if wanted & set(e.sub_questions)][:3]
    qs = [questions[i] for i in section.get("questions", []) if i < len(questions)]
    lines = [f"*The library does not have enough evidence for this section: it needs {standards.min_facts} facts from "
             f"{standards.min_docs} documents and found {support['facts']} fact(s) from {support['documents']} "
             f"document(s).*", ""]
    if qs:
        lines += ["Questions this section was meant to answer:", *[f"- {q}" for q in qs], ""]
    if own:
        lines += ["What the library does say:", *[f"- {_gist(e)} [{e.id}]" for e in own], ""]
    else:
        lines += ["The library holds nothing relevant to these questions.", ""]
    if qs:
        lines.append("To fill this gap, collect sources about: " + "; ".join(q.rstrip("?") for q in qs) + ".")
    return "\n".join(lines).rstrip()


def _gist(e) -> str:
    """One line for a gap note: the fact itself, or for a v3 passage its document and the start of its text."""
    if not getattr(e, "passage", False):
        return e.claim
    text = re.sub(r"\s+", " ", re.sub(r"^\[[^\]]*\]\s*", "", e.quote)).strip()
    text = text if len(text) <= 220 else text[:220].rsplit(" ", 1)[0] + " ..."
    return f"{e.source}: \"{text}\""


def gaps_and_next_steps(supports: dict[int, dict], questions: list[str]) -> str:
    """Replaces the recommendations section of a gap report: no recommendation, only what to do next."""
    weak = [s for s in supports.values() if s["status"] != "supported"]
    lines = ["*This report cannot give a recommendation: too little of what the goal asks about is covered by the library.*", "",
             "Covered well enough: " + (", ".join(s["title"] for s in supports.values() if s["status"] == "supported") or "nothing"),
             "", "Not covered, and what to collect for each:"]
    for s in weak:
        qs = [questions[i].rstrip("?") for i in s["questions"] if i < len(questions)]
        lines.append(f"- **{s['title']}** ({s['facts']} fact(s), {s['documents']} document(s)): " + ("; ".join(qs) or "no questions recorded"))
    lines += ["", "Next step: run again and, at plan approval, choose to collect sources for the questions the library does not "
                  "cover, then choose the PDFs and web pages to keep."]
    return "\n".join(lines)


# ---- repeats and filler ----------------------------------------------------------------------------------

_FILLER = re.compile(r"(?i)^(the goal of this section|in this section|this section (will|aims|explores|examines|discusses)|"
                     r"further research is needed|more research is needed)\b")
_WORD = re.compile(r"[a-z0-9]+")


def _sentences(text: str) -> list[str]:
    """Sentences of one line. Does not split after common abbreviations or inside numbers (0.78)."""
    parts, start = [], 0
    for m in re.finditer(r"(?<=[.!?])\s+", text):
        before = text[start:m.start()].split()[-1:] or [""]
        if before[0].lower() in {"e.g.", "i.e.", "vs.", "etc.", "approx.", "fig.", "al."}:
            continue
        parts.append(text[start:m.start()])
        start = m.end()
    parts.append(text[start:])
    merged: list[str] = []
    for part in parts:
        lead = re.match(r"\s*((?:\[E\d+\])+)[.\s]*", part)
        if merged and lead:                                  # "Foo bar. [E3] Next one.": [E3] belongs to "Foo bar."
            merged[-1] = merged[-1].rstrip() + " " + lead.group(1)
            part = part[lead.end():]
        if part.strip():
            merged.append(part)
    return merged


def strip_filler(text: str) -> str:
    """Remove sentences that announce or hedge instead of saying something (the small model's favourite padding)."""
    out = []
    for line in text.split("\n"):
        if line.lstrip().startswith(("|", "#", ">")) or not line.strip():
            out.append(line)
            continue
        kept = [s for s in _sentences(line) if not _FILLER.match(s.strip(" *-•0123456789."))]
        out.append(" ".join(kept) if kept else "")
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def _paragraph_words(p: str) -> set[str]:
    return set(_WORD.findall(re.sub(r"\[E\d+\]", " ", p.lower())))


def dedupe_sections(sections: list[tuple[str, str]], threshold: float = 0.8) -> list[tuple[str, str]]:
    """Drop a paragraph that repeats an earlier one (word overlap at or above the threshold). Tables, headings, lists, short
    paragraphs and generated notes are never touched."""
    seen: list[set[str]] = []
    out = []
    for title, body in sections:
        if is_generated(body):
            out.append((title, body))
            continue
        kept = []
        for para in re.split(r"\n\s*\n", body):
            words = _paragraph_words(para)
            structural = para.lstrip().startswith(("|", "#", "-", "*", ">")) or len(words) < 12
            if not structural and any(len(words & s) / max(len(words | s), 1) >= threshold for s in seen):
                continue
            if not structural:
                seen.append(words)
            kept.append(para)
        out.append((title, "\n\n".join(kept).strip()))
    return out


# ---- numbers and claim labels ----------------------------------------------------------------------------

_CITE = re.compile(r"\[E(\d+)\]")
_NUM = re.compile(r"\d[\d,]*\.?\d*")


def _numbers(text: str) -> set[str]:
    """Numeric tokens worth checking: two or more digits, or a decimal (single digits like '3 sections' are too common)."""
    found = set()
    for tok in _NUM.findall(text):
        tok = tok.replace(",", "").rstrip(".")
        if len(tok.replace(".", "")) >= 2 or "." in tok:
            found.add(tok)
    return found


def evidence_numbers(evidence: list) -> set[str]:
    return set().union(*(_numbers(f"{e.claim} {e.quote}") for e in evidence)) if evidence else set()


# Model names and sizes: "4B", "1.7B", "367M", "Qwen3-1.7B", "LLaMA-3", "gemma4", "GPT-4o" (a word with a letter and a digit).
_SIZE = re.compile(r"(?<![\w.])\d+(?:\.\d+)?\s?[BM](?![\w])")
_NAME = re.compile(r"(?<![\w-])[A-Za-z][A-Za-z.]*-?\d[\w.]*(?:-[\w.]+)*")


def _squash(text: str) -> str:
    return re.sub(r"[\s\-_]+", "", text.lower())


def subjects(text: str) -> set[str]:
    """The model sizes and model-like names a sentence mentions (citations [E3] are not names)."""
    text = _CITE.sub(" ", text)
    found = {m.group(0).replace(" ", "") for m in _SIZE.finditer(text)}
    found |= {m.group(0).rstrip(".") for m in _NAME.finditer(text) if not re.fullmatch(r"E\d+", m.group(0))}
    return found


def missing_subjects(sentence: str, cited: list) -> set[str]:
    """Subjects the sentence names that appear neither in the cited evidence nor in its document titles. This is the E-001
    check: "pretraining a 4B model ... [E7]" where E7 is a post-training paper that never says 4B."""
    haystack = _squash(" ".join(f"{e.claim} {e.quote} {e.source}" for e in cited))
    return {s for s in subjects(sentence) if _squash(s) not in haystack and _variant(s) not in haystack}


def _variant(name: str) -> str:
    """The name without a release suffix, so "Qwen3-4B-Instruct" matches a source that writes "Qwen3-4B-Inst."."""
    return re.sub(r"(instruct|inst|chat|base|it)\.?$", "", _squash(name))


def label_text(text: str, by_id: dict, known_numbers: set[str], flags_only: bool = False) -> str:
    """Append a support label to every sentence of prose: [established] (cited, 2+ documents), [single source] (1 document),
    [inference] (no citation) or [inference: figures not from sources] (no citation and a number that appears in no evidence).
    A cited sentence whose number or model name/size is not in the cited evidence gets a flag instead. With ``flags_only``
    a cited sentence that passes the checks gets no tag. Tables, headings and quotes are left alone."""
    out = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith(("|", "#", ">", "```")) or stripped.startswith("*The library"):
            out.append(line)
            continue
        labelled = []
        for sent in _sentences(line):
            if len(sent.split()) < 4:
                labelled.append(sent)
                continue
            ids = {int(n) for n in _CITE.findall(sent)}
            cited = [by_id[f"E{n}"] for n in ids if f"E{n}" in by_id]
            docs = {e.source for e in cited}
            cited_numbers = evidence_numbers(cited)
            if docs and _numbers(_CITE.sub("", sent)) - cited_numbers:
                tag = "[cited; figure not in the cited evidence]"      # a citation does not make an invented number true
            elif docs and missing_subjects(sent, cited):
                tag = "[cited; subject not in the cited evidence]"     # E-001: the right number on the wrong model
            elif docs and flags_only:
                labelled.append(sent)
                continue
            elif len(docs) >= 2:
                tag = "[established]"
            elif len(docs) == 1:
                tag = "[single source]"
            elif _numbers(sent) - known_numbers:
                tag = "[inference: figures not from sources]"
            else:
                tag = "[inference]"
            labelled.append(f"{sent.rstrip()} {tag}")
        out.append(" ".join(labelled))
    return "\n".join(out)
