"""Quality audit of one finished research run, from its trace (<vault>/.desk/desk.sqlite), its report and the library.

  python scripts/audit_run.py <run id prefix> [--judge-swapped] [--out evals/v3/audit_<id>.json]

1. Run health: steps and times, model calls by step/role, failures, thinking fallbacks, repairs.
2. Reranker: per question, the hybrid order vs the reranked order of the pool; chunks the writer saw that hybrid alone would
   not have put in its top 8 ("rescued"); with --judge-swapped, the model also grades the chunks hybrid's top 8 had but the
   reranker swapped out, so the share of useful chunks (grade >= 2) in hybrid's top 8 and the reranker's top 8 can be
   compared on the same questions.
3. The writer's use of its passages per section: given, cited, unused.
4. Claim support: word coverage of every cited sentence by the chunk(s) it cites; the weakest are listed for reading.
5. Sources used, by document.
"""
import argparse
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from _common import ROOT  # noqa: E402

from research_assistant import deep_report as d  # noqa: E402
from research_assistant import report_checks as rc  # noqa: E402

VAULT = Path(r"C:\Users\me\ObsidianVaults\Research")
DESK = VAULT / ".desk" / "desk.sqlite"
KB = VAULT / ".kb" / "library.sqlite"


def q(db, sql, *args):
    return db.execute(sql, args).fetchall()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--judge-swapped", action="store_true")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    db = sqlite3.connect(f"file:{DESK}?mode=ro", uri=True)
    kb = sqlite3.connect(f"file:{KB}?mode=ro", uri=True)
    rid, goal, engine, plan, stats, path, settings = q(
        db, "select run_id, goal, engine, plan, stats, report_path, settings from runs where run_id like ?", a.run + "%")[0]
    plan, stats = json.loads(plan), json.loads(stats)
    out: dict = {"run": rid, "engine": engine, "settings": json.loads(settings)}

    # 1. health ------------------------------------------------------------------------------------------------------
    print(f"RUN {rid} engine {engine}\nreport {Path(path).name}\n")
    steps = q(db, "select name, outcome, round(seconds) from steps where run_id=? order by id", rid)
    print("steps:", ", ".join(f"{n} {s}s" + ("" if o == "ok" else f" ({o})") for n, o, s in steps if s))
    calls = q(db, "select step, role, count(*), round(sum(seconds)), sum(1-ok), sum(answer_chars=0) from llm_calls "
                  "where run_id=? group by step, role", rid)
    print("model calls (step/role: n, seconds, failed, empty answers):")
    for c in calls:
        print(f"   {c[0]:10} {c[1]:8} n={c[2]:3} {c[3]:5}s failed={c[4]} empty={c[5]}")
    keys = ("llm_calls", "llm_gave_up", "llm_off_topic", "llm_cited_sentences", "llm_citations_repaired",
            "llm_tables_dropped", "llm_passages_not_given", "llm_thinking_fallbacks", "evidence", "words")
    print("stats:", {k.replace("llm_", ""): stats.get(k) for k in keys})
    out["health"] = {"steps": steps, "calls": calls, "stats": {k: stats.get(k) for k in keys}}

    # 2. reranker ----------------------------------------------------------------------------------------------------
    print("\nRERANKER (pool of 24 per question; the writer path keeps the reranked top 8, then the 0-3 grade)")
    rer = defaultdict(list)
    for row in q(db, "select question_idx, question, rank, hybrid_rank, rerank_score, chunk_id, text_hash, doc_title "
                     "from retrievals where run_id=? order by question_idx, rank", rid):
        rer[row[0]].append(row)
    graded = {(qi, h): (s, k) for qi, h, s, k in q(db, "select question_idx, text_hash, score, kept from judgements where run_id=?", rid)}
    totals = {"rescued": 0, "kept": 0, "swapped_out": 0}
    swapped_for_judging = []
    per_q = []
    for qi, rows in rer.items():
        question = rows[0][1]
        top8 = [r for r in rows if r[2] <= 8]
        hybrid_top8 = [r for r in rows if r[3] is not None and r[3] <= 8]
        kept = [r for r in top8 if graded.get((qi, r[6]), (0, 0))[1]]
        rescued = [r for r in kept if r[3] and r[3] > 8]
        swapped = [r for r in hybrid_top8 if r[2] > 8]
        totals["rescued"] += len(rescued)
        totals["kept"] += len(kept)
        totals["swapped_out"] += len(swapped)
        scores_kept = [r[4] for r in top8 if graded.get((qi, r[6]), (0, 0))[1]]
        scores_rej = [r[4] for r in top8 if not graded.get((qi, r[6]), (0, 0))[1]]
        print(f" Q{qi + 1}: kept {len(kept)}/8 | rescued from hybrid ranks {sorted(r[3] for r in rescued)} | "
              f"swapped out of hybrid's top 8: {len(swapped)} | rerank score kept avg "
              f"{(sum(scores_kept) / len(scores_kept)) if scores_kept else float('nan'):.2f} vs rejected "
              f"{(sum(scores_rej) / len(scores_rej)) if scores_rej else float('nan'):.2f}")
        per_q.append({"q": qi, "kept": len(kept), "rescued_from": sorted(r[3] for r in rescued), "swapped_out": len(swapped)})
        swapped_for_judging += [(qi, question, r) for r in swapped]
    print(f" total: {totals['kept']} kept, {totals['rescued']} of them rescued from below hybrid's top 8 "
          f"({totals['rescued'] / max(totals['kept'], 1):.0%}); {totals['swapped_out']} hybrid-top-8 chunks swapped out")
    out["reranker"] = {"per_question": per_q, **totals}

    if a.judge_swapped and swapped_for_judging:
        llm = d.ollama_llm("qwen3.5:4b", temperature=0, reasoning=False)
        goal_text = d._clip(d.model_goal(goal), 700)
        useful_swapped = 0
        for qi, question, r in swapped_for_judging:
            text = kb.execute("select text from chunks where id=?", (r[5],)).fetchone()
            raw = d._obj(d._json(llm(d.RELEVANT_PROMPT.format(question=question, goal=goal_text, source=r[7], heading="-",
                                                              passage=d._clip(text[0] if text else "", d.MAX_PASSAGE_CHARS)),
                                     json_mode=True), {}))
            try:
                useful_swapped += int(raw.get("score", 0)) >= d.MIN_PASSAGE_SCORE
            except (TypeError, ValueError):
                pass
        # hybrid's top 8 = the chunks both kept in the top 8 + the swapped-out ones
        n_q = len(rer)
        both_useful = sum(1 for qi, rows in rer.items() for r in rows
                          if r[2] <= 8 and r[3] and r[3] <= 8 and graded.get((qi, r[6]), (0, 0))[1])
        rerank_useful = totals["kept"]
        hybrid_useful = both_useful + useful_swapped
        print(f" head-to-head over {n_q} questions x 8: useful chunks in the reranker's top 8 = {rerank_useful}, "
              f"in hybrid's top 8 = {hybrid_useful} (swapped-out chunks graded useful: {useful_swapped}/{len(swapped_for_judging)})")
        out["reranker"]["head_to_head"] = {"rerank_useful": rerank_useful, "hybrid_useful": hybrid_useful,
                                           "swapped_useful": useful_swapped, "swapped": len(swapped_for_judging)}

    # 3. writer's use ------------------------------------------------------------------------------------------------
    md = Path(path).read_text(encoding="utf-8")
    sentences = q(db, "select section, text, cites, flag from sentences where run_id=?", rid)
    cited_by_section = defaultdict(set)
    for sec, _, cites, _ in sentences:
        cited_by_section[sec] |= set(json.loads(cites))
    print("\nWRITER (passages given -> cited per section)")
    use = []
    given = defaultdict(list)
    for sec, eid, inc in q(db, "select section, eid, included from section_inputs where run_id=? order by id", rid):
        if inc:
            given[sec].append(eid)
    for sec, eids in given.items():
        used = [e for e in eids if e in cited_by_section[sec]]
        print(f" {sec[:34]:34} given {len(eids)}, cited {len(used)}, unused {sorted(set(eids) - set(used))}")
        use.append({"section": sec, "given": len(eids), "cited": len(used)})
    out["writer"] = use

    # 4. claim support -----------------------------------------------------------------------------------------------
    texts = {eid: (kb.execute("select text from chunks where id=?", (cid,)).fetchone() or ("",))[0] + " " + (title or "")
             for eid, cid, title in q(db, "select eid, chunk_id, doc_title from evidence where run_id=?", rid)}
    cov = []
    for sec, text, cites, flag in sentences:
        ids = json.loads(cites)
        if ids:
            c = max(rc.coverage(text, texts.get(i, "")) for i in ids)
            cov.append((round(c, 2), sec, text, ids, flag))
    cov.sort()
    buckets = {"<0.3": sum(c < 0.3 for c, *_ in cov), "0.3-0.5": sum(0.3 <= c < 0.5 for c, *_ in cov),
               "0.5-0.7": sum(0.5 <= c < 0.7 for c, *_ in cov), ">=0.7": sum(c >= 0.7 for c, *_ in cov)}
    flags = defaultdict(int)
    for *_, f in sentences:
        flags[f or "clean"] += 1
    print(f"\nCLAIMS: {len(sentences)} sentences, flags {dict(flags)}; cited-sentence word coverage by its chunk: {buckets}")
    print(" weakest cited sentences (read these against their chunks):")
    for c, sec, text, ids, flag in cov[:8]:
        print(f"   {c:.2f} [{','.join(ids)}] {sec[:22]}: {text[:150]}")
    out["claims"] = {"sentences": len(sentences), "flags": dict(flags), "coverage": buckets,
                     "weakest": [{"coverage": c, "section": s, "text": t, "cites": i} for c, s, t, i, _ in cov[:8]]}

    # 5. sources -----------------------------------------------------------------------------------------------------
    docs = q(db, "select doc_title, kind, count(*) from evidence where run_id=? group by doc_title order by 3 desc", rid)
    cited_docs = {r[0] for r in q(db, "select distinct e.doc_title from evidence e where e.run_id=?", rid)}
    print(f"\nSOURCES: {len(docs)} documents in the evidence")
    for title, kind, n in docs:
        print(f"   {n:2} x {kind or '?':4} {title[:90]}")
    out["sources"] = [{"title": t, "kind": k, "passages": n} for t, k, n in docs]
    words = len(re.sub(r"\[[^\]]*\]", "", "\n".join(line for line in md.split("## Limitations")[0].splitlines()
                                                     if not line.startswith("|"))).split())
    print(f"\nreport main text: {words} words; questions {len(plan.get('questions', []))}; cited docs {len(cited_docs)}")
    out["report_words"] = words
    target = Path(a.out or ROOT / "evals" / "v3" / f"audit_{rid[:8]}.json")
    target.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("->", target)


if __name__ == "__main__":
    sys.exit(main())
