"""Error analysis (P0.1): sample claims from saved reports, label them, tally where the wrong ones first went wrong.

  python scripts/error_analysis.py build  REPORT.md [REPORT.md ...] [--n 50] [--seed 1] [--kb PATH]
  python scripts/error_analysis.py tally  [--who human|claude]

build writes evals/error_analysis/claims.xlsx (sheet "How to label" + sheet "Claims" with the evidence in each row and
dropdowns for the labels: the human labels go here), claims.csv (the same rows, plain) and claims.md (readable: each
claim with its cited facts, quotes and the library passage around each quote). Re-running build with the same
reports, n and seed gives the same sample; it refuses to overwrite a sheet that already has labels.

Labelling is blind: Claude's labels live in claude_labels.csv (id, verdict, stage, note), so the human labeller does
not see them; tally joins the two by id. Labels typed in claims.xlsx win over claims.csv.

Labels: verdict ok | wrong; stage = the FIRST stage that went wrong, for a wrong claim:
  retrieval miss      the right source was never found (shows as a gap, rarely as a cited claim)
  bad source          the source is off-goal (excluded modality, wrong domain or kind of document)
  extraction subject  the extracted fact misstates the source's subject or scope (often in the question's words)
  writing subject     the fact is right, the report sentence drops or changes its subject or meaning
  writing stitch      facts from different sources joined into one claim that none of them makes
  label               content fine, evidence label wrong (e.g. "established" on one document, inference stated as fact)
  other
"""
import argparse
import csv
import re
import sys
from pathlib import Path

from _common import ROOT  # noqa: E402

from research_assistant import eval_tools as et  # noqa: E402
from research_assistant.knowledge import default_kb_path  # noqa: E402

OUT = ROOT / "evals" / "error_analysis"
FIELDS = ["id", "report", "section", "kind", "label", "claim", "cites", "human_verdict", "human_stage", "human_note"]
CLAUDE = OUT / "claude_labels.csv"
WORKBOOK = OUT / "claims.xlsx"
EXCERPT = 1200

GUIDE = [
    ("How to label the 50 claims", ""),
    ("What you judge", "The CLAIM: the report sentence in the 'claim' column. Not the quote: quotes are always verbatim "
     "(the code checks that, which is exactly why wrong claims slipped through). Ask: if I read this sentence in the "
     "report, would it mislead me about the goal?"),
    ("Where to work", "Sheet 'Claims'. Fill only the three yellow columns: human_verdict, human_stage, human_note. Each "
     "row's 'evidence' cell has, for every cited fact: the FACT the pipeline extracted, the verbatim QUOTE, the SOURCE, "
     "and the library PASSAGE around the quote (the quote is marked >>like this<<)."),
    ("Dropdowns", "Click a yellow cell: a short help pops up and an arrow opens the dropdown. human_verdict and "
     "human_stage accept only list values; human_note offers common reasons but you can type your own. Sheet "
     "'Dropdown options' explains every value."),
    ("Step 1", "Read the claim. What does it tell you?"),
    ("Step 2", "Read the source and passage in 'evidence'. What is the source really about: which model, what size, "
     "pretraining or fine-tuning, text or speech?"),
    ("Step 3", "Compare. Same thing, honestly stated: human_verdict = ok. Different thing, or overstated: wrong."),
    ("Step 4 (only if wrong)", "Find where it FIRST broke, walking source -> fact -> claim, and pick human_stage:"),
    ("bad source", "The source doesn't fit the goal (e.g. a speech model when the user said text only; a school "
     "essay-writing guide used as evidence about LLM reasoning)."),
    ("extraction subject", "The extracted fact (the 'FACT:' line) already names the wrong model, size or stage, or turns "
     "the source's statement into a general rule (often in the research question's words)."),
    ("writing subject", "The fact is right, but the report sentence drops or changes what it is about (e.g. one "
     "project's settings presented as what 'the model' must do)."),
    ("writing stitch", "Facts from different sources merged into one claim that none of them makes."),
    ("label", "Content fine, evidence label wrong: 'established' needs two or more documents saying the same thing; a "
     "recommendation drawn from one source is an inference, not 'single source'."),
    ("retrieval miss / other", "Retrieval miss = the right source was never found (rare for a cited claim). Other = "
     "anything else; say what in human_note."),
    ("Worked example: C34", "Claim: 'use optimal hyperparameters for a 4B model: batch size 4 [E7], weight decay 0.001 "
     "[E8]', labelled established. Source: an appendix table in a paper about EVALUATING POST-TRAINED models; nothing "
     "about pretraining a 4B model. Fact E7: 'optimal hyperparameters for pretraining a 4B model include batch size 4': "
     "already wrong. Verdict: wrong. Stage: extraction subject (the first break is the fact; the claim only repeats it)."),
    ("Tip: 'the model'", "If a claim says 'the model' or 'this process', check the sentence before it in the report "
     "(claims.md, or the report itself): often the subject was named there, and then the claim is ok."),
    ("Tip: weak relevance", "True but only weakly relevant (e.g. it names a 295B frontier model in a 4B-8B report): ok, "
     "with a note. Use wrong only when the sentence would actually mislead."),
    ("Blind labelling", "Don't open claude_labels.csv (or its commit) until you are done; the agreement score depends "
     "on it."),
    ("When done", "Save the workbook (keep .xlsx), then run: python scripts/error_analysis.py tally"),
]


def excerpt(passage: str, quote: str) -> str:
    """The passage around the quote, with the quote marked, at most EXCERPT characters."""
    flat = re.sub(r"\s+", " ", passage).strip()
    q = re.sub(r"\s+", " ", quote.replace("\\|", "|")).strip()
    at = flat.lower().find(q.lower())
    if at < 0:
        return flat[:EXCERPT]
    start = max(0, at - (EXCERPT - len(q)) // 2)
    piece = flat[start:start + max(EXCERPT, len(q) + 40)]
    i = piece.lower().find(q.lower())
    marked = piece[:i] + "**>>" + piece[i:i + len(q)] + "<<**" + piece[i + len(q):] if i >= 0 else piece
    return ("…" if start else "") + marked + ("…" if start + len(piece) < len(flat) else "")


def has_labels() -> bool:
    csv_path = OUT / "claims.csv"
    in_csv = csv_path.exists() and any(r.get("human_verdict") for r in read_rows(csv_path))
    in_book = WORKBOOK.exists() and any(v["human_verdict"] for v in et.read_label_workbook(WORKBOOK).values())
    return in_csv or in_book


def build(args):
    csv_path, md_path = OUT / "claims.csv", OUT / "claims.md"
    if has_labels():
        sys.exit("The sheet already has labels; move claims.csv / claims.xlsx away first if you want a new sample.")
    finder = et.PassageFinder(args.kb)
    pool, evidence = [], {}
    for path in map(Path, args.reports):
        md = path.read_text(encoding="utf-8")
        name = path.stem[:40]
        evidence[name] = et.parse_evidence(md)
        for c in et.parse_claims(md):
            if c["cites"]:                                   # uncited claims cannot be traced; they are counted separately
                pool.append({**c, "report": name})
    sample = et.stratified_sample(pool, args.n, seed=args.seed)
    OUT.mkdir(parents=True, exist_ok=True)
    rows, blocks = [], []
    for i, c in enumerate(sample, 1):
        cid = f"C{i:02d}"
        lines = [f"## {cid} · {c['report']} · {c['section']}", "",
                 f"**Claim** ({c['kind']}, label: {c['label'] or 'none'}):", "", f"> {c['text']}", ""]
        cell = []                                            # the same evidence, for the workbook's "evidence" column
        for eid in c["cites"]:
            ev = evidence[c["report"]].get(eid)
            if not ev:
                lines += [f"- **{eid}**: not in the evidence appendix", ""]
                cell.append(f"{eid}: not in the evidence appendix")
                continue
            hit = finder.find(ev["quote"], ev["source"])
            passage = excerpt(hit["passage"], ev["quote"]) if hit else "(passage not found in the library)"
            lines += [f"- **{eid}** fact: {ev['claim']}", f"  - quote: \"{ev['quote']}\"", f"  - source: {ev['source']}",
                      f"  - passage: {passage}", ""]
            cell.append(f"{eid} FACT: {ev['claim']}\nQUOTE: \"{ev['quote']}\"\nSOURCE: {ev['source']}\n"
                        f"PASSAGE: {passage.replace('**>>', '>>').replace('<<**', '<<')}")
        lines += ["Verdict: ok / wrong · Stage if wrong: retrieval miss / bad source / extraction subject / "
                  "writing subject / writing stitch / label / other", "", "---", ""]
        blocks.append("\n".join(lines))
        rows.append({"id": cid, "report": c["report"], "section": c["section"], "kind": c["kind"], "label": c["label"],
                     "claim": c["text"], "cites": " ".join(c["cites"]), "evidence": "\n\n".join(cell)})
    with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    et.write_label_workbook(rows, WORKBOOK, GUIDE)
    head = (f"# Error analysis sheet\n\n{len(rows)} claims sampled (seed {args.seed}) from {len(args.reports)} reports, "
            f"pool of {len(pool)} cited claims. Label in `claims.xlsx` (guide on its first sheet).\n"
            "Stage = the FIRST stage that went wrong. `**>>quote<<**` marks the quote inside its passage.\n\n---\n\n")
    md_path.write_text(head + "\n".join(blocks), encoding="utf-8")
    print(f"wrote {WORKBOOK}, {csv_path} and {md_path}: {len(rows)} claims from a pool of {len(pool)}")


def read_rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def tally(args):
    rows = read_rows(OUT / "claims.csv")
    if WORKBOOK.exists():                                    # labels typed in the workbook win over the csv
        typed = et.read_label_workbook(WORKBOOK)
        for r in rows:
            if any(typed.get(r["id"], {}).values()):
                r.update(typed[r["id"]])
    claude = {r["id"]: r for r in read_rows(CLAUDE)} if CLAUDE.exists() else {}
    for r in rows:
        c = claude.get(r["id"], {})
        r.update(claude_verdict=c.get("verdict", ""), claude_stage=c.get("stage", ""), claude_note=c.get("note", ""))
    for who in ([args.who] if args.who else ["human", "claude"]):
        b = et.stage_breakdown(rows, verdict=f"{who}_verdict", stage=f"{who}_stage")
        print(f"\n{who}: {b['labelled']} labelled, {b['ok']} ok, {b['wrong']} wrong")
        for stage, n in sorted(b["stages"].items(), key=lambda kv: -kv[1]):
            print(f"  {stage:<20} {n:>3}  ({n / b['wrong']:.0%} of wrong)")
        if not b["labelled"]:
            print("  (no labels yet)")
    both = [(r["human_verdict"], r["claude_verdict"]) for r in rows if r["human_verdict"] and r["claude_verdict"]]
    pairs = [("y" if h.strip().lower() == "ok" else "n", "y" if c.strip().lower() == "ok" else "n") for h, c in both]
    a = et.agreement(pairs)
    if a["n"]:
        print(f"\nverdict agreement human vs claude: {a['agree']}/{a['n']} ({a['rate']:.0%}), kappa {a['kappa']:.2f}")
        for r in rows:
            if r["human_verdict"] and r["claude_verdict"] and (r["human_verdict"], r["human_stage"]) != (r["claude_verdict"], r["claude_stage"]):
                print(f"  disagree {r['id']}: human {r['human_verdict']}/{r['human_stage']} vs claude {r['claude_verdict']}/{r['claude_stage']}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("reports", nargs="+")
    b.add_argument("--n", type=int, default=50)
    b.add_argument("--seed", type=int, default=1)
    b.add_argument("--kb", default=default_kb_path())
    t = sub.add_parser("tally")
    t.add_argument("--who", choices=["human", "claude"])
    args = p.parse_args()
    build(args) if args.cmd == "build" else tally(args)


if __name__ == "__main__":
    main()
