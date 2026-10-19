"""Build evals/subject_facts.jsonl (P0.2): the extraction subject eval set.

  python scripts/build_subject_eval.py [--vault PATH] [--kb PATH]

Each case is a real evidence row from the two saved reports of 2026-10-02 and 2026-10-03, with the library passage
it came from, the research question it was read for, and hand-labelled expected fields (system, size, stage, and
modality/task where they matter). ``v1_fact`` is what the v1 pipeline extracted and ``v1_subject_ok`` says whether
that fact named the source's real subject: the v1 baseline for the scoreboard. Labels by Claude (2026-10-19), to be
spot-checked by the user (U-02 sits on the same reports).
"""
import argparse
import json
import os
import re
from pathlib import Path

from _common import ROOT  # noqa: E402

from research_assistant import eval_tools as et  # noqa: E402
from research_assistant.knowledge import default_kb_path  # noqa: E402

REPORTS = {"10-02": "Research/2026-10-02-building-a-small-language-model-with-strong-reasoning-and-re.md",
           "10-03": "Research/2026-10-03-pretraining-a-4b-model-for-telugu-english-and-transliteratio.md"}
Q02 = ("Building a 4B-8B small language model with strong reasoning and reliable tool calling for Telugu, English and "
       "Tenglish (text only)")
Q03 = ("How to pretrain a 4B model from scratch for Telugu, English and transliteration, good at reasoning and native "
       "tool calling")
KNOWN = {"E7", "E8", "E79", "E76", "E40"}             # the E-001 cases, tagged in "origin" so tests can find them
POST = "models evaluated in 'Thinking About Thinking: Evaluating Reasoning in Post-Trained Language Models'"
PAVAN = "pavanmantha/qwen3-4b-telugu-transliteration"
TLLM = "Telugu-learning LLM project (fine-tuning LLaMA 3 8B)"
WHISPER = "jayasuryajsk/whisper-large-v3-Telugu-Romanized"
TRANSLIT = {"task": "Telugu-to-Roman transliteration"}
SPEECH = {"modality": "speech"}

# (report, evidence id, question, system, size, stage, extra expected fields, v1 fact subject ok?, note)
CASES = [
    ("10-03", "E7", Q03, POST, "unknown", "post-training", {}, False,
     "E-001: appendix hyperparameters of a post-training study, not optimal 4B pretraining settings"),
    ("10-03", "E8", Q03, POST, "unknown", "post-training", {}, False, "E-001: same table as E7"),
    ("10-03", "E79", Q03, "Param2-17B-A2.4B-Thinking", "17B (2.4B active)", "pretraining", {}, False,
     "E-001: 22.63T tokens is the 17B MoE's total, not a 4B requirement"),
    ("10-03", "E48", Q03, "Param2-17B-A2.4B", "17B (2.4B active)", "pretraining", {}, True, "fact names the right system"),
    ("10-03", "E76", Q03, PAVAN, "4B", "fine-tuning", TRANSLIT, False,
     "E-001: fine-tune hardware extracted as pretraining requirements"),
    ("10-03", "E40", Q03, PAVAN, "4B", "fine-tuning", TRANSLIT, True,
     "fact is right; the report later used it as a pretraining recipe"),
    ("10-03", "E10", Q03, PAVAN, "4B", "none", {}, True, "parameter count of a fine-tuned model"),
    ("10-03", "E15", Q03, PAVAN, "4B", "fine-tuning", TRANSLIT, False,
     "SFT loss on assistant tokens extracted as the pretraining objective for a 4B model"),
    ("10-03", "E31", Q03, PAVAN, "4B", "fine-tuning", {}, False,
     "quote says 'Full fine-tune with DDP'; fact says the 4B model is pretrained"),
    ("10-03", "E75", Q03, PAVAN, "4B", "fine-tuning", {}, False,
     "padding setting of a fine-tune, extracted as a pretraining setting of 'the Qwen3-4B model'"),
    ("10-03", "E9", Q03, PAVAN, "4B", "fine-tuning", TRANSLIT, True, ""),
    ("10-03", "E42", Q03, "Paramanu (367M configuration)", "367M", "none", {}, False,
     "table row is the 367M model; fact says 'the 4B model'"),
    ("10-03", "E77", Q03, "Paramanu", "unknown", "pretraining", {}, True, "fact drops the system but claims no wrong one"),
    ("10-03", "E78", Q03, "NEZHA (byte-level subword multilingual PLM)", "unknown", "pretraining", {}, False,
     "fact drops NEZHA; reads as a general pretraining batch size"),
    ("10-03", "E45", Q03, "IndicBART", "unknown", "pretraining", {}, False,
     "fact turns IndicBART's corpus into 'the model should be trained on'"),
    ("10-03", "E46", Q03, "IndicBART", "unknown", "none", {"task": "multilingual seq2seq (11 Indian languages + English)"},
     False, "fact adds 'transliteration' and 'should'"),
    ("10-03", "E26", Q03, WHISPER, "unknown", "evaluation", SPEECH, True,
     "speech ASR metric; the report presented it as transliteration WER"),
    ("10-03", "E57", Q03, "language models studied in ALERT", "unknown", "fine-tuning", {}, True, ""),
    ("10-03", "E61", Q03, "Qwen3-1.7B", "1.7B", "evaluation", {}, True, ""),
    ("10-03", "E52", Q03, "Reason-then-Act prompting baseline on Qwen3-1.7B", "1.7B", "inference", {}, True,
     "a prompt mode, not a fine-tuning method"),
    ("10-03", "E29", Q03, "2:4 sparse training on NVIDIA Ampere GPUs", "unknown", "pretraining", {}, True, ""),
    ("10-03", "E34", Q03, "parameter-efficient finetuning (general)", "n/a", "fine-tuning", {}, True, ""),
    ("10-02", "E10", Q02, "IndicBERT-v3-4B", "4B", "continued pretraining", {"task": "bidirectional encoder (MNTP)"}, True,
     "encoder, not a generative model"),
    ("10-02", "E11", Q02, "IndicBERT-v3-4B", "4B", "continued pretraining", {"task": "bidirectional encoder (MNTP)"}, True, ""),
    ("10-02", "E13", Q02, "IndicBERT-v3-4B", "4B", "continued pretraining", {}, True, ""),
    ("10-02", "E14", Q02, TLLM, "8B", "fine-tuning", {}, False,
     "a project's plan extracted as 'the LLaMA 3 8B model requires'"),
    ("10-02", "E30", Q02, TLLM, "8B", "fine-tuning", {}, False,
     "one project's hardware becomes general requirements for Telugu/English/Tenglish fine-tuning"),
    ("10-02", "E39", Q02, TLLM, "8B", "fine-tuning", {}, False, "project feature list becomes a model requirement"),
    ("10-02", "E46", Q02, TLLM, "8B", "fine-tuning", {}, False, "fact adds 'pretraining'; the project only fine-tunes"),
    ("10-02", "E17", Q02, "Aya-Expanse 8B", "8B", "none", {}, True, ""),
    ("10-02", "E21", Q02, "Aya-Expanse 8B", "8B", "none", {}, True, ""),
    ("10-02", "E23", Q02, "Aya-Expanse 8B", "8B", "inference", {}, True, ""),
    ("10-02", "E4", Q02, WHISPER, "unknown", "fine-tuning", SPEECH, True, "speech model; the goal is text only"),
    ("10-02", "E59", Q02, WHISPER, "unknown", "fine-tuning", SPEECH, False,
     "fact says 'the model' without naming the speech model"),
    ("10-02", "E50", Q02, "TeluguST-46 (speech translation benchmark)", "n/a", "evaluation", SPEECH, True,
     "speech; the goal is text only"),
    ("10-02", "E51", Q02, "systems fine-tuned in TeluguST-46 (speech translation)", "unknown", "fine-tuning", SPEECH, False,
     "'The model can be fine-tuned with a mix' drops the speech-translation subject"),
    ("10-02", "E62", Q02, "DeepSeek-R1-Distill-Qwen", "1.5B", "post-training", {}, True, "RL fine-tuning on 7,000 examples"),
    ("10-02", "E75", Q02, "Hy3 (Tencent)", "295B (21B active)", "inference", {}, True, "frontier MoE, outside 4B-8B"),
    ("10-02", "E79", Q02, "Gemini 3.8 Flash", "unknown", "none", {}, True, "frontier model"),
    ("10-02", "E101", Q02, "ToolBench-X fault-injection harness", "n/a", "evaluation", {}, False,
     "a benchmark harness rule extracted as a requirement of reliable tool calling"),
    ("10-02", "E97", Q02, "ToolBench-X tool construction rules", "n/a", "evaluation", {}, False,
     "'All tools must not involve image processing' becomes a property of reliable tool calling"),
    ("10-02", "E65", Q02, "EBA Skill #2 (school essay-writing guide)", "n/a", "none",
     {"task": "argumentative writing, not LLM reasoning"}, False,
     "essay advice extracted as a definition of strong reasoning for the model"),
]
MAX_PASSAGE = 1800


def passage_for(finder: et.PassageFinder, ev: dict) -> tuple[str, bool]:
    """The library passage around the quote (at most MAX_PASSAGE chars), or the quote alone when the source page was
    never indexed (the source title still carries the subject)."""
    hit = finder.find(ev["quote"], ev["source"])
    if not hit:
        return f"[{ev['source']}]\n{ev['quote']}", False
    flat = re.sub(r"\s+", " ", hit["passage"]).strip()
    if len(flat) > MAX_PASSAGE:
        at = max(0, flat.lower().find(re.sub(r"\s+", " ", ev["quote"]).lower()[:60]))
        flat = flat[max(0, at - 700):max(0, at - 700) + MAX_PASSAGE]
    return f"[{hit['doc']}]\n{flat}", True


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--vault", default=os.environ.get("VAULT_PATH", ""))
    p.add_argument("--kb", default=default_kb_path())
    args = p.parse_args()
    evidence = {k: et.parse_evidence((Path(args.vault) / rel).read_text(encoding="utf-8")) for k, rel in REPORTS.items()}
    finder = et.PassageFinder(args.kb)
    out = []
    for i, (rep, eid, q, system, size, stage, extra, ok, note) in enumerate(CASES, 1):
        ev = evidence[rep][eid]
        passage, found = passage_for(finder, ev)
        out.append({"id": f"S{i:02d}", "origin": f"{eid},{rep}:{eid}" if eid in KNOWN else f"{rep}:{eid}",
                    "source": ev["source"], "question": q, "passage": passage, "passage_from_library": found,
                    "expected": {"system": system, "size": size, "stage": stage, **extra},
                    "v1_fact": ev["claim"], "v1_subject_ok": ok, "note": note})
    target = ROOT / "evals" / "subject_facts.jsonl"
    target.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in out) + "\n", encoding="utf-8")
    et.load_subject_cases(target)                       # validates every stage
    print(f"{len(out)} cases -> {target}; {sum(c['passage_from_library'] for c in out)} with library passages; "
          f"v1 subject right in {sum(c['v1_subject_ok'] for c in out)}/{len(out)}")


if __name__ == "__main__":
    main()
