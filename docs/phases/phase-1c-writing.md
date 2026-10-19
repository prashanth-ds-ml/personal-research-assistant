# Phase 1c: Writing (selection, decision, critique-and-revise, checks, claim check view)

**Goal:** the writing step reasons over all selected facts at once and
produces a report whose numbers, labels and decision hold up.

**Depends on:** P1b gate. Task order follows the P1a-0 error analysis; critique → revise only if P1a-T09 showed it pays.
**Scope items:** P1.26, P1.3, P1.4, P1.11, P1.12, P1.13, P1.14, P1.15, P1.16, P1.17 (kept), E-001 (provenance and label part).

## Tasks

- [ ] Report types: decision brief and state of the evidence (plan templates, chapter shapes).
- [ ] Options become questions and a decision (one question per named option).
- [ ] Selection within L7 (≤80 facts) by relevance, tier, novelty; set-aside list.
- [ ] Decision step over all selected facts: options, criteria, for/against, choice or "evidence cannot decide"; thinking on.
- [ ] Chapters written from facts; **critique → revise** loop via `Command` (1-2 rounds; critique as structured output: unsupported claims, stitched numbers, missing counter-evidence, repetition).
- [ ] Summary written from the decision.
- [ ] Number provenance check in code; stitched sentences relabelled as synthesis or rewritten.
- [ ] Label rules in code: established ≥2 agreeing documents / single source / synthesis / inference.
- [ ] Report shows collected / read / used counts ("239 indexed for later") and the gaps.
- [ ] Prompt token budgets enforced and logged for every call.
- [ ] **Claim check view (P1.26)**: in the report reader, click a claim → its fact(s) → source passage with the quote highlighted; label and number provenance shown; works on the committed sample report.

## Test cases

| ID | Type | Case | Expected |
|---|---|---|---|
| P1c-T01 | Unit | Goal naming pretrain / continue / fine-tune | Plan has one question per option + decision |
| P1c-T02 | Budget | 140 candidate facts, L7=80 | 80 selected; writing prompt within budget; set-aside listed |
| P1c-T03 | Golden | Saved SLM evidence → decision | States a choice with reasons and limits, or "cannot decide" with why |
| P1c-T04 | Unit | Sentence with numbers from two facts of different sources | Flagged; relabelled synthesis or rewritten |
| P1c-T05 | Golden | Report-2 summary case (4 sources stitched) | No "established" label; numbers traced |
| P1c-T06 | Unit | Claim backed by one document | Labelled single source, never established |
| P1c-T07 | Unit | Critique finds an unsupported claim | Revise round removes or supports it; max rounds respected |
| P1c-T08 | Unit | Summary vs decision overlap | < 50% |
| P1c-T09 | Golden | 100% of numbers in summary and decision | Each traces to one fact |
| P1c-T10 | Adversarial | Out-of-coverage goal | Gap report, no filler (existing behaviour kept) |
| P1c-T11 | Budget | Every call in a full run | No prompt over its budget (log check) |
| P1c-T12 | Unit | Claim → fact → passage lookup for every claim in a report | Every claim resolves; quote found verbatim in the passage |
| P1c-T13 | Manual | Claim check view on the sample report | One click to a highlighted quote; numbers and label visible |
| P1c-T14 | Golden | Scoreboard on 3 gold goals | Beats the raw-passage baseline on numbers traced, label errors and blind score |

## Review items
- Read the full SLM report end to end; compare with report_v6_mix.md.
- Decision reasoning cites facts, not chapters.

## Exit gate
- [ ] All test cases pass; full offline suite green.
- [ ] E-001 closed (both parts); scoreboard column "P1c" filled.
- [ ] No open Critical/High errors for P1c.

## Results
_Fill in at the gate._
