# Web collector - design (not built yet)

Status: **built 2026-10-01** (`src/research_assistant/collector.py`, tests in `tests/test_collector.py`, graph steps
`discover` -> `review` -> `collect`, dashboard review card on `/deep`). Live-tested on a real goal: 40 candidates
found in about 2.5 minutes, 3 chosen, 2 saved and indexed, report written.

Differences from the design below: seed URLs are collected through the same sequential path (as `seed` candidates);
the candidate list is capped per question (an equal share of the total) so early questions cannot use it all up;
per-run options are saved in the run's state (the dashboard sends them only with the first call; resumes carry
none); `scripts/collect.py` still collects papers only (no `--web` yet). Not built: recursive crawling inside a site.
Decision record: see "The web collector is one agent, and we write our own fetching" in `DECISIONS.md`.

## 1. Problem
Deep research answers only from the local library. The fetcher can add arXiv and Europe PMC open-access papers
and URLs the user types in, but it cannot *find* web pages. For goals that need guidelines, laws, vendor docs or
blog posts (for example the sexual-health assistant in project 6), the user has to collect sources by hand first.

## 2. Goal and non-goals
> **v2.1 (2026-10-18):** ticking is replaced by plan + collection-rule approval and the 40-candidate cap is removed (SCOPE section 5, P1.22). This doc describes the code as built before that change.

**Goal.** When "Fetch new sources" is ticked, find candidate web pages and papers for each plan question, show
them to the user, save the approved ones as markdown in the library, and let the normal research step use them.

**Non-goals.** No paid search APIs. No JavaScript rendering in v1. No crawling of whole sites in v1. No parallel
fetching. No fetching at chat time in project 6 (that project reads only reviewed, saved sources).

## 3. User flow
1. Tick **Fetch new sources**, answer the clarifying questions, approve the plan (unchanged).
2. **Discover**: for each plan question, one after another, search the web and open-access paper APIs.
3. **Review candidates** (new pause): a list with title, site, the question it serves, the relevance score 0-3,
   and whether it is a paper or a web page. Score 3 is pre-ticked. The user can tick or untick any of them.
4. **Collect**: fetch the ticked candidates one at a time, convert to markdown, save, write the manifest.
5. The library refreshes (existing `refresh` logic) and research and writing run as before.

## 4. Architecture
One module, `src/research_assistant/collector.py`, is an independent agent with a plain interface. It is used by
the deep-research graph and by `scripts/collect.py`. It is not a separate LangGraph graph.

```
collector.discover(questions, settings)  -> list[Candidate]          # search + dedupe + triage, downloads nothing
collector.collect(candidates, settings)  -> CollectReport             # fetch + convert + save, sequential
```

- `Candidate`: `id, url, title, site, kind (paper|page), question_index, score (0-3), reason, snippet`.
- **Search backends** behind one small function `search(query, n) -> list[Hit]`:
  `ddgs` (default, already a dependency), SearXNG if `SEARXNG_URL` is set, arXiv and Europe PMC via the existing
  fetcher APIs. Backend failure returns a warning, not an exception (same rule as the current `collect`).
- **Triage**: the existing relevance judge (local model, one call per candidate, sees title + snippet + first
  ~1500 characters of the page), default keep score 3. A fixed cap of candidates per question (default 8) bounds
  the cost.
- **Fetching** reuses `Fetcher` from `fetcher.py`: public-host-only check with redirect re-validation, robots.txt,
  per-host delay (arXiv at least 3 s), 40 MB cap, dedupe by id / URL / content hash.
- **Conversion**: HTML goes through `trafilatura` (already used) to markdown with tables; PDFs go through
  Docling (existing). Both write front matter: `source_url`, `fetched_at`, `question`, `kind`, `score`, `license_note`.
- **Output folder**: `<vault>/Library/<date>-<goal-slug>/` with the markdown files and `manifest.json`
  (saved / skipped / failed, each with a reason). Same folder convention as today.
- **Trust marking**: pages carry `kind: page` and papers `kind: paper`; the report's Limitations section states how
  many web pages versus papers were used.

## 5. Graph changes (`goal_graph.py`)
Current: `... approve -> collect -> research ...`. New: `approve -> discover -> review (interrupt) -> collect ->
research ...`. `discover` and `collect` are thin nodes that call the module. The `review` interrupt has the same
shape as `approve`: value `{type: "review_sources", candidates: [...]}`; resume value `{selected: [ids]}`.
If no candidates are found, skip the pause and say so in the status.

## 6. Dashboard (`/deep`)
- New card "Sources found" shown for the `review_sources` interrupt: grouped by question, each row a checkbox,
  title as a link (opens in a new tab), site, score badge, one-line reason. Buttons: "Collect selected",
  "Skip fetching".
- Existing "Fetched sources" status line stays; add "web pages / papers" counts.

## 7. Configuration
New settings (env or per-run where noted; paths and URLs stay environment-only, like the rest):
`SEARCH_BACKEND` (ddgs|searxng), `SEARXNG_URL`, `COLLECT_ALLOW_DOMAINS` (optional allow-list, for example
`who.int;cdc.gov;nhs.uk;*.gov.in`), `COLLECT_BLOCK_DOMAINS`, `COLLECT_CANDIDATES_PER_QUESTION` (8),
`FETCH_MAX_SOURCES` (existing), `COLLECT_REVIEW` (true; false = auto-accept score 3, for unattended runs).
Per-run allowed: the review toggle and the allow-list choice only.

## 8. Safety and politeness
Same guards as the fetcher. Additionally: only `http(s)`; never follow a link found *inside* a fetched page
(candidates come from search only); sanitize file names; treat fetched text as untrusted data in every prompt
(existing delimiters); respect `robots.txt` and `noindex`; one request at a time.

## 9. Tests (offline)
Fake search backend and fake fetcher. Cases: dedupe across questions; already-in-library is dropped; allow-list
and block-list; triage threshold; backend failure yields a warning; review interrupt resume with a subset; empty
candidates skips the pause; manifest contents; sequential order (one in flight); SSRF and redirect still refused.
Live check: one real goal, then read the manifest.

## 10. Build order
1. `collector.py` + tests + `scripts/collect.py --web`.
2. Graph nodes and interrupt + flow tests.
3. Dashboard card + walkthrough script support (`--fetch-web`).
4. Live run on a real goal; record the result in `EVALS.md`; update README and runbook.

## 11. Open questions (decide while building)
- Whether `ddgs` returns enough useful results for guideline and law queries; if not, prefer SearXNG or an
  allow-list with site-restricted queries (`site:who.int ...`).
- Whether to add `RecursiveUrlLoader`-style crawling inside one trusted site (v2, on our fetcher).
- How to show licence information: only a note in front matter for now; content is for private use.

## 12. What we keep from LangChain
Nothing new from LangChain's web loaders (they lack our network guards). LangChain stays in use for the model
and embedding wrappers, as before.
