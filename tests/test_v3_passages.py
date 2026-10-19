"""v3 M1: reports written from library passages with one model (docs/SCOPE.md). Offline: fake search, fake model."""
import json

from research_assistant import deep_report, goal_graph
from research_assistant import eval_tools as et
from research_assistant import report_checks as rc
from research_assistant.configuration import Configuration

POST = {"title": "Thinking About Thinking: Evaluating Reasoning in Post-Trained Language Models",
        "heading": "Appendix B › Hyperparameters", "text": "Batch size | 4 | Weight decay | 0.001 | Learning rate 1e-5",
        "path": "post.pdf", "source_url": "", "source_kind": "pdf"}
CARD = {"title": "Qwen3-4B model card", "heading": "Training", "text": "Qwen3-4B was pretrained on 36T tokens.",
        "path": "card.md", "source_url": "https://hf.co/q", "source_kind": "web"}
SPEECH = {"title": "Whisper Telugu", "heading": "", "text": "WER 12.4 on Telugu speech.", "path": "w.md",
          "source_url": "", "source_kind": "web"}


def plan(questions=("What batch size?", "How many tokens?")):
    return deep_report.Plan(goal="Pretrain a 4B model", title="T", sub_questions=list(questions),
                            outline=[{"title": "Setup", "questions": list(range(len(questions))), "brief": ""}])


def judge(useful_titles, prompts=None):
    def llm(prompt, json_mode=False):
        if prompts is not None:
            prompts.append(prompt)
        return json.dumps({"score": 2 if any(f'"{t}"' in prompt for t in useful_titles) else 1})
    return llm


def test_M1_T01_passages_are_the_evidence_kept_once_and_judged_per_question():
    deep_report.reset_stats()
    prompts: list[str] = []
    ev = deep_report.gather_evidence(plan(), lambda q: [POST, CARD, SPEECH], judge({POST["title"], CARD["title"]}, prompts),
                                     passages=True)
    assert [e.id for e in ev] == ["E1", "E2"]
    assert all(e.passage for e in ev)
    assert ev[0].quote == POST["text"] and ev[0].source == POST["title"]
    assert ev[0].claim == f"{POST['title']} › Appendix B › Hyperparameters"            # where the passage sits
    assert ev[0].sub_questions == [0, 1]                                                 # found again for Q2: kept once
    assert sum("useful evidence" in p for p in prompts) == 4                             # 3 judged for Q1, only SPEECH again for Q2
    assert deep_report.snapshot_stats()["off_topic"] == 2                                # rejected per question: Q1 and Q2
    assert all("Pretrain a 4B model" in p for p in prompts)                              # the goal is in every judgement


def test_M1_T02_resume_keeps_earlier_passages_and_continues():
    first = deep_report.gather_evidence(plan(("Q1",)), lambda q: [POST], judge({POST["title"]}), passages=True)
    done = []
    ev = deep_report.gather_evidence(plan(("Q1", "Q2")), lambda q: [CARD], judge({CARD["title"]}), passages=True,
                                     resume=(1, first), on_question_done=lambda d, t, e: done.append(d))
    assert [e.source for e in ev] == [POST["title"], CARD["title"]] and done == [2]


def test_M1_T03_the_writer_sees_whole_passages_with_their_location_and_the_v3_rules():
    ev = deep_report.gather_evidence(plan(), lambda q: [POST, CARD], judge({POST["title"], CARD["title"]}), passages=True)
    seen = []
    body = deep_report.write_section(plan().outline[0], plan(), ev, lambda p, json_mode=False: seen.append(p) or
                                     "Qwen3-4B was pretrained on 36T tokens [E2].")
    prompt = seen[0]
    assert "[E1] Thinking About Thinking" in prompt and "Batch size | 4 |" in prompt and "36T tokens" in prompt
    assert "150-300 words" in prompt and "Read the document title" in prompt
    assert "Extract facts" not in prompt and "[E2]" in body


def test_M1_T04_passage_budget_counts_what_does_not_fit():
    items = [deep_report.Evidence(id=f"E{i}", claim=f"Doc {i}", quote="x" * 1000, source=f"D{i}", heading="",
                                  sub_questions=[0], passage=True) for i in range(1, 6)]
    block = deep_report._passage_block(items, limit=2_500)
    assert "[E1]" in block and "[E2]" in block and "[E3]" not in block
    assert "(3 more passages omitted to fit the model's context)" in block


def test_M1_T05_subject_check_flags_the_E001_sentence_and_passes_honest_ones():
    ev = [deep_report.Evidence(id="E1", claim=f"{POST['title']} › Appendix B", quote=POST["text"], source=POST["title"],
                               heading="", sub_questions=[0], passage=True),
          deep_report.Evidence(id="E2", claim="Qwen3-4B model card › Training", quote=CARD["text"], source=CARD["title"],
                               heading="", sub_questions=[0], passage=True)]
    by_id = {e.id: e for e in ev}
    known = rc.evidence_numbers(ev)
    bad = rc.label_text("For pretraining a 4B model, use a weight decay of 0.001 [E1].", by_id, known, flags_only=True)
    assert bad.endswith("[E1] [cited; subject not in the cited evidence].")           # E-001: 4B is not in E1; tag before the stop
    ok = rc.label_text("A post-training study used a weight decay of 0.001 [E1].", by_id, known, flags_only=True)
    assert ok == "A post-training study used a weight decay of 0.001 [E1]."            # passes: no tag at all
    named = rc.label_text("Qwen3-4B was pretrained on 36T tokens [E2].", by_id, known, flags_only=True)
    assert "[cited;" not in named
    wrong_number = rc.label_text("Qwen3-4B was pretrained on 18T tokens [E2].", by_id, known, flags_only=True)
    assert "[cited; figure not in the cited evidence]" in wrong_number
    uncited = rc.label_text("Small models need careful data selection.", by_id, known, flags_only=True)
    assert uncited.endswith("[inference].")
    full = rc.label_text("A post-training study used a weight decay of 0.001 [E1].", by_id, known)
    assert full.endswith("[single source]")                                            # v2 labels unchanged without flags_only


def test_M1_T06_subjects_finds_sizes_and_model_names_not_citations():
    assert rc.subjects("Qwen3-1.7B beat LLaMA-3 8B and a 367M encoder [E12].") >= {"Qwen3-1.7B", "LLaMA-3", "8B", "367M"}
    assert not any(s.startswith("E1") for s in rc.subjects("see [E12]"))


def test_M1_T07_report_appendix_shows_passages_and_still_parses():
    ev = deep_report.gather_evidence(plan(), lambda q: [POST, CARD], judge({POST["title"], CARD["title"]}), passages=True)
    sections = [("Setup", "Qwen3-4B was pretrained on 36T tokens [E2]. A post-training study used batch size 4 [E1].")]
    report = deep_report.assemble(plan(), sections, ev, lambda p, json_mode=False: "Summary [E2].",
                                  standards=rc.Standards(min_facts=1, min_docs=1, flags_only=True))
    assert "| ID | Where | Passage | Source |" in report
    assert "Code checks that each number and each model name or size" in report
    parsed = et.parse_evidence(report)
    assert parsed["E2"]["quote"] == CARD["text"] and parsed["E1"]["source"] == POST["title"]
    assert "[single source]" not in report                                             # flags only


def test_M1_T08_one_model_in_every_role_thinking_off(monkeypatch):
    calls = []
    monkeypatch.setattr(deep_report, "ollama_llm", lambda model, url, **kw: calls.append((model, kw)) or (lambda p: ""))
    goal_graph.build_llms(Configuration(local_llm="qwen3.5:4b"))
    assert {m for m, _ in calls} == {"qwen3.5:4b"}
    assert [kw["reasoning"] for _, kw in calls] == [False, False, False, False]        # planner, extractor, writer, thinker
    calls.clear()
    goal_graph.build_llms(Configuration(local_llm="qwen3.5:4b", plan_thinking=True))
    assert [kw["reasoning"] for _, kw in calls] == [False, False, False, True]         # only the planning step thinks
    assert deep_report.NUM_CTX == 16_384


def test_M1_T09_passage_score_threshold_and_unreadable_answers():
    answers = iter(['{"score": 3}', '{"score": 1}', 'not json', '{"score": "2"}'])
    hits = [dict(CARD, text=f"passage {i}", title=f"Doc {i}", path=f"d{i}.md") for i in range(4)]
    ev = deep_report.gather_evidence(plan(("Q",)), lambda q: hits, lambda p, json_mode=False: next(answers), passages=True)
    assert [e.source for e in ev] == ["Doc 0", "Doc 3"]                                 # 3 and "2" kept; 1 and garbage not


def test_M1_T10_gap_notes_quote_the_start_of_each_passage_not_its_location():
    ev = [deep_report.Evidence(id="E1", claim="Doc A › 4.2 Setup", quote="[Doc A > 4.2 Setup] We train for 3 epochs.",
                               source="Doc A", heading="4.2 Setup", sub_questions=[0], passage=True)]
    note = rc.gap_note({"title": "S", "questions": [0]}, {"facts": 1, "documents": 1}, ["Q?"], ev, rc.Standards())
    assert '- Doc A: "We train for 3 epochs." [E1]' in note


def test_M1_T11_two_passages_from_two_documents_carry_a_section_by_default():
    assert Configuration().min_section_facts == 2


def test_M1_T12_release_suffix_variants_are_the_same_model():
    ev = [deep_report.Evidence(id="E1", claim="Paper", quote="| Qwen3-4B-Inst. | 0.948 |", source="Paper", heading="",
                               sub_questions=[0], passage=True)]
    assert not rc.missing_subjects("Qwen3-4B-Instruct reached 0.948 [E1].", ev)
    assert rc.missing_subjects("Qwen3-8B-Instruct reached 0.948 [E1].", ev) == {"Qwen3-8B-Instruct", "8B"}


def test_M1_T13_thinking_uses_qwen_sampling_a_big_budget_and_a_long_deadline(monkeypatch):
    import langchain_ollama
    seen = {}

    class FakeChat:
        def __init__(self, **kw):
            seen.update(kw)

        def stream(self, prompt):
            class C:
                content = '{"ok": true}'
            yield C()

    monkeypatch.setattr(langchain_ollama, "ChatOllama", FakeChat)
    deadlines = []
    real = deep_report.consume
    monkeypatch.setattr(deep_report, "consume", lambda s, **kw: deadlines.append(kw["deadline_s"]) or real(s, **kw))
    deep_report.ollama_llm("qwen3.5:4b", temperature=0, reasoning=True)("plan", json_mode=True)
    assert seen["temperature"] == 0.6 and seen["top_p"] == 0.95 and seen["top_k"] == 20      # never greedy when thinking
    assert seen["num_predict"] == deep_report.JSON_MAX_TOKENS + deep_report.THINK_TOKENS
    assert deadlines == [deep_report.THINK_DEADLINE]
    seen.clear()
    deep_report.ollama_llm("qwen3.5:4b", temperature=0, reasoning=False)("plan", json_mode=True)
    assert seen["temperature"] == 0 and "top_k" not in seen and seen["num_predict"] == deep_report.JSON_MAX_TOKENS
