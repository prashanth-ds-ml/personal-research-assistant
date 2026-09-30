# Deep research demo (~3 minutes)

**Before recording:** the library is ingested (`scripts/ingest_library.py`), Ollama
is running with `llama3.1:8b`, `gemma4:e4b` and `qwen3-embedding:0.6b`, and both
services were restarted after the last update (the dashboard needs
`npm run build`, the backend must be restarted to register the `deep_research`
graph). Pre-run the goal once so the report exists in case the live run is slow
(a run takes about 11-12 minutes; narrate over the wait or cut).

**One-line pitch:** *"Give it a goal, it asks what it needs to know, shows you a
plan, then writes a long cited report from your own documents - all on local
models, nothing leaves the machine."*

1. **The problem (20s).** Open the library folder: 11 PDFs. *"A team has a pile of
   papers and policies. Nobody has time to read them all before a decision."*
2. **Enter the goal** on the **Deep Research** page: *"How should a small team
   build a reliable retrieval-augmented generation system on small local
   models?"* Click Start.
3. **It asks before it acts (30s).** The run pauses and shows clarifying
   questions. Answer two of them, leave one blank. *"It's not guessing scope. This
   is a LangGraph interrupt - the run is paused, not polling."*
4. **Plan approval (30s).** Show the sub-questions and outline; type a revision
   ("add a section on cost") and click Revise, then Approve. *"Nothing expensive
   ran yet. The plan is the contract."*
5. **While it runs (30s).** Show the status line. Explain the pipeline in one
   breath: *"It retrieves with keyword plus vector search, extracts facts passage
   by passage, throws away any fact whose quote isn't literally in the source,
   asks a second model call to confirm the passage supports it, then writes one
   section at a time."*
6. **Open the finished report (45s).** Show: the executive summary, a section with
   a table, `[E7]`-style citations. Click to the **Evidence appendix**: each
   citation maps to a claim, a verbatim quote and the paper. *"Every sentence is
   traceable. Where the library had nothing, the section says so instead of
   guessing."*
7. **The numbers (30s).** Open EVALS.md: hybrid search 80% recall@1 vs 68% BM25
   vs 48% vectors on 25 labelled questions; the table of report quality after each
   fix. *"I didn't stop at 'it looks good' - here's what each fix changed."*
8. **The honest close (15s).** *"It's a cited first draft for an expert, not a
   finished document - it can still merge two true findings into a false one, and
   here's the test that shows where. For a customer I'd start with the discovery
   questionnaire and a labelled sample of their documents."*

## If asked
- **Why local models?** Data never leaves the machine; cost is time, not money.
- **Why not one big prompt?** Small models need small jobs; see DECISIONS.md.
- **How do you know the judge is any good?** The labelling sheet and scorer
  exist; report the score only after labelling (do not claim it before).
- **What would you do with a bigger model?** Swap `DOCKER_WRITER_MODEL` /
  `DOCKER_PLANNER_MODEL`; the eval harness tells you if it helped.
