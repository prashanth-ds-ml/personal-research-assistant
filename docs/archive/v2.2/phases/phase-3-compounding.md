# Phase 3: Compounding knowledge

**Goal:** the library gets more valuable with use: later reports reuse
checked facts, and the user can see freshness, contradictions and health.

**Depends on:** P2 gate.
**Scope items:** P3.1-P3.5.

## Tasks

- [ ] Reports from the library only (collect off), reusing fact-bank facts before re-reading.
- [ ] Fact reuse: skip re-extraction for (source, similar question) already read (cache + fact bank lookup).
- [ ] Freshness: newest source per collection; "may be outdated" warnings in chat and reports.
- [ ] Contradiction view: facts on the same subject that disagree.
- [ ] Collection health: duplicates, junk, stale sources, coverage map.
- [ ] Cross-thread chat memory (preferences, current topic) with `SqliteStore` + Ollama embeddings.

## Test cases

| ID | Type | Case | Expected |
|---|---|---|---|
| P3-T01 | Integration | Second report on a related goal | ≥ 30% facts reused; faster; quality not lower (blind) |
| P3-T02 | Unit | Collection newest source 6 months old | Warning shown in chat and report |
| P3-T03 | Golden | Seeded collection with 2 contradicting facts | Shown side by side with sources |
| P3-T04 | Unit | Health on seeded duplicates/junk | All flagged |
| P3-T05 | Unit | Reused fact provenance | Original run and source kept |

## Exit gate
- [ ] All test cases pass; SCOPE section 8 Phase 3 acceptance met; no open Critical/High errors.

## Results
_Fill in at the gate._
