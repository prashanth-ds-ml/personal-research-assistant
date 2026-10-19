# Build plan (finalized 2026-09-30)

> **Superseded for planning by [`SCOPE.md`](SCOPE.md) v2 (2026-10-12) and [`STATUS.md`](STATUS.md).** Kept as history; open items from here are carried into the phase docs and `ERROR_LOG.md`.

Goal: get the research assistant from "feature-complete demo" to "a tool I use every
week, with numbers that prove it works". Scope is only what is already built or
already on the roadmap: wiring fix, judge scoring, collector, real documents,
demo. Nothing else.

## Status

- **M0 done (2026-09-30).** Library path unified (`knowledge.default_kb_path`; the library now lives at `<vault>/.kb/library.sqlite` with 11 papers + 66 archived web pages = 77 documents, 2,465 chunks). OCR off by default with automatic fallback for scans. Planner temperature 0. Services restarted and the autostart script fixed (it could not find the shared venv). The full clarify -> revise -> approve -> report flow was run through the dashboard's own API proxy with real models: 4 clarifying questions, a revised plan, then a 5,362-word report from 12 sources (9 papers + 3 archived pages), no empty sections, saved to the vault, rendered by the dashboard (HTTP 200, 7 tables, 118 citations). 42 offline tests. **Not verified:** a real browser click-through (no console-error check); that remains a 2-minute manual check.
- Bugs found and fixed on the way (details in DECISIONS.md): ingest pruned other folders' documents; the start script could not start the backend; planning lost its recommendations section when the goal carried clarification text; revision requests could be ignored.
- **M1 preliminary (2026-09-30):** all 50 claims labelled by Claude (`claude` column) and the judge scored against them: 0 false accepts of 25-26 accepted (rule not triggered; llama stays the judge), 5-6 false rejects of 31 supported (too strict, mostly table numbers), gemma4:e4b better on this sheet (1 false reject, 1 false accept). **Needs a human pass** on the 8 contestable rows (ids 2, 9, 11, 16, 25, 31, 34, 39) before the numbers are final; see EVALS.md section 3.
- **Lean plan built (2026-09-30):** step 2 auto-ingest (new files in `Sources/` and `Library/` are indexed at the start of each run), step 3 the small source fetcher (arXiv + Europe PMC + seed URLs; live-tested: 3 papers fetched, converted with Docling, saved with provenance, indexed), step 4 one-click feedback read by the planner (live-tested dashboard -> vault -> planner path). 73 offline tests. A live end-to-end acceptance run (autonomous, fetching on, a new file dropped into the library first) indexed the new file at run start and cited it in the report, fetched 2 sources, skipped 2 duplicates from the earlier run, and recorded 1 timeout as a failure without stopping. It also showed the triage was too loose at relevance 2 (a visual-QA and a code-generation paper got in), so the default bar is now 3. Step 1 (use it on real topics) is yours.
- **Still optional:** the 8 faithfulness labels (only for the proof number); a separate judge-model setting if human labels confirm gemma judges better.

## Revised plan (2026-09-30, after review): lean and usable

Decision: stop adding agent steps; make it useful and make it grow. (The 8 faithfulness labels are
optional, only for the proof number.) The old M2-M6 are replaced by:

1. **Use it on 2-3 real topics** and note every failure. (You; drives everything below.)
2. **Auto-ingest:** deep research re-indexes new files in the configured source folders at the
   start of each run (cheap: unchanged files are skipped by hash). Exit: drop a PDF in the folder,
   start a run, it is searchable without running any script.
3. **Small source fetcher (not a scraper):** from the plan's questions, fetch open-access papers
   from arXiv and Europe PMC (official APIs, rate limits honored) plus seed URLs you give it
   (robots.txt honored); relevance-triage before saving; save with provenance; cap per run; off
   unless you tick the box. Exit: offline tests on canned responses; one real run that adds papers
   to the library and shows up in the next report.
4. **One-click feedback on each report** (useful / not + note), saved with the report; the planner
   reads the last few notes. Exit: rating saved in the report's frontmatter and visible in the next
   plan prompt.

Left out on purpose: swarm, more model sweeps, extra dashboard pages, broad web
crawling, CUDA, further portfolio polish until real use exists.

## Research findings that change the plan

Checked against primary sources where possible; each row says how sure we are.

| # | Finding | Effect on the plan | Confidence |
|---|---|---|---|
| R1 | **Docling OCR is unnecessary for our PDFs and is most of the cost.** Docling's own benchmark says turning OCR off saves about 60% of CPU time. On our machine, one paper: **77 s with OCR vs 21 s without, output identical** (same 67,303 characters, same 79 table rows, similarity 1.0). OCR is on by default. | Default `do_ocr=False`; fall back to OCR only when a PDF yields almost no text (scanned). Ingesting a 30-paper collection drops from about 40 min to about 10. | Measured here |
| R2 | A CUDA build of PyTorch would speed Docling about 5x (Docling reports 7.9 vs 1.5 pages/s on an RTX 5090 vs CPU). | **Dropped from the roadmap.** With OCR off, CPU is fast enough; CUDA adds install risk on a Blackwell laptop GPU for little gain. | Docs + measured R1 |
| R4 | **arXiv API: at most one request every 3 seconds, one connection at a time;** no bulk PDF through the API (bulk is S3). | Collector paces arXiv at 3 s minimum, single connection, fetches only the PDFs for selected papers. Cap per goal keeps this small. | Terms of use page via search |
| R5 | **Europe PMC REST API: no key or account; full text (XML) only for its Open Access subset.** NCBI E-utilities: 3 requests/s, 10 with a free API key. | For health topics, discover via PubMed/Europe PMC and take **full text only from open-access articles**; for everything else store the abstract and link, nothing more. | Search summaries; confirm at build time |
| R6 | **OpenAlex** (free; its docs say no key required, 100k credits/day, 100 requests/s; list query costs 10 credits; adding a `mailto` puts you in the faster "polite pool") exposes the open-access location of a paper. | Use OpenAlex for discovery and to find legal OA PDF links. One search result hinted that API keys may become required; design the key as an optional environment variable. | Docs read |
| R7 | **Unpaywall's API may have been retired** (one search summary said 18 September 2026). The official page returned no content, so this is **unverified**. | **Do not depend on Unpaywall.** OpenAlex already carries the same open-access data (R6). | Unverified |
| R8 | **trafilatura** is the best article extractor in published comparisons: F1 0.937 vs 0.914 (readability-lxml) and 0.903 (newspaper3k), with precision 0.978. | Use trafilatura for web pages. | Benchmarks via search |
| R9 | Python's `urllib.robotparser` handles `can_fetch` and `crawl_delay`, but has open bug reports about `crawl_delay` and `request_rate` edge cases. | Use it for allow/deny; enforce our own minimum interval per domain (3 s) regardless, and honor a larger `Crawl-delay` when given. | Docs + bug tracker via search |

## Decisions (made now, so building does not stall)

1. **Sources, in order of preference:** official APIs (arXiv, Europe PMC/PubMed, OpenAlex) > your own seed URLs > general web search. Every source is tagged with where it came from and its licence/access note.
2. **Legal line:** respect `robots.txt` and each API's terms and rate limits; skip paywalled or login pages; open-access full text only; collected content stays private and is never republished.
3. **Identification:** a real user-agent with a contact email (also earns OpenAlex's polite pool).
4. **Cap:** 30-60 sources per goal.
5. **Planner temperature 0** for reproducibility (the plan currently varies between 5 and 7 sections run to run).
6. **Model roles:** llama plans and extracts, gemma writes (measured).
7. **Library location:** one knowledge base, `<vault>/.kb/library.sqlite`, created and used by both the ingest script and the graph. Current mismatch is fixed in Milestone 0.

## Milestones

Each has an exit test; do not start the next until it passes. Effort: S = one sitting, M = a few, L = more.

### M0. Make it usable (S) - **this is "start using"**
- Fix the library path (graph vs built library) and add `KB_PATH` to `.env.example`.
- Ingest: `do_ocr=False` by default, OCR fallback when a PDF has almost no extractable text; test both paths.
- Planner temperature 0.
- Restart services (dashboard build + backend) and walk the Deep Research page in a browser: clarify, revise plan, approve, report opens. Fix what breaks.
- Ingest the vault's existing notes too (same ingest tool, one more folder) so research builds on past research.
- **Exit:** a real report from the dashboard, from the real library, opens in the dashboard; no console errors; unit tests still green.

### M1. Trust number (S, plus 10 min from you)
- You label the 50-claim sheet; I score the judge.
- **Decision rule, fixed in advance:** if more than 10% of judge-accepted claims are actually unsupported, try a different-family judge (gemma) on the same sheet and keep whichever is better; if neither is under 10%, say so in EVALS.md and lower the README's claims accordingly.
- **Exit:** false-accept and false-reject rates published in EVALS.md.

### M2. Collector (L)
- `collector.py` and `scripts/collect.py "<goal>"`: candidates from arXiv / Europe PMC / OpenAlex APIs, your seeds, then web search; relevance triage by the local model on title + snippet (score 0-3) before any download; polite fetch; trafilatura for pages; Docling (OCR off) for PDFs; `Sources/<goal>/{raw,md,manifest.json}` with provenance frontmatter; dedupe by normalized URL, content hash and near-duplicate text; incremental ingest into the library.
- Offline tests with canned API/HTML/PDF responses (no network), including robots.txt deny, rate-limit spacing and dedupe.
- **Quality test:** on one goal where you list 10 known-good sources, report precision and recall of what was kept, and what was skipped and why (from the manifest).
- **Exit:** numbers in EVALS.md; manifest lists every skip with a reason.

### M3. Wire collector into the graph (M)
- A skippable `collect` node after plan approval; dashboard line: found / kept / skipped.
- **Exit:** same goal with and without collection, compared on papers used, cited facts, empty sections.

### M4. Real documents (M, needs you)
- A de-identified set from your own work plus 20 questions with known answers.
- **Exit:** retrieval recall on your set reported next to the public-paper set; one deep report on it reviewed by you.

### M5. Package (S, needs you)
- Record the 3-minute demo; update the README, diagram and demo script.

### Only if the numbers justify it
Feedback loop (report ratings feed the planner), questions mid-run when blocked, a stronger writer model.

## Order to start using it
M0 and M1 make it a real, measured tool (about two sittings plus your 10 minutes). M2 and M3 add capability, each gated by a test that can say no. M4 and M5 turn it into the portfolio story.

## Sources (research)
- arXiv API terms of use: https://info.arxiv.org/help/api/tou.html and bulk access: https://info.arxiv.org/help/bulk_data/index.html
- OpenAlex rate limits and authentication: https://github.com/ourresearch/openalex-docs/blob/main/how-to-use-the-api/rate-limits-and-authentication.md
- NCBI E-utilities API key: https://support.nlm.nih.gov/kbArticle/?pn=KA-05317
- Europe PMC NAR paper (REST API, open-access full text): https://academic.oup.com/nar/article/46/D1/D1254/4637578
- Trafilatura benchmarks: https://trafilatura.readthedocs.io/en/latest/evaluation.html
- Docling GPU and pipeline options: https://docling-project.github.io/docling/usage/gpu/ and https://docling-project.github.io/docling/reference/pipeline_options/ (benchmarks in https://arxiv.org/pdf/2501.17887)
- Python robots.txt parser: https://docs.python.org/3/library/urllib.robotparser.html (bugs: https://bugs.python.org/issue35922)
