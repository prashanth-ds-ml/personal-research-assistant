# Reliability check + demo script

## Reliability check: does personalization actually change behavior?

The core claim of this project isn't "it can search the web" (the stock
tutorial already does that) - it's "it gets better at helping *you*
specifically the more you use it." That's the thing worth verifying, since
it's easy to build the plumbing (profile note, vault retrieval) without it
actually affecting anything.

**Test**: run two related topics back-to-back and check three things.

1. **Source archive populates.** After a run, `Sources/<date>-<topic>/`
   should contain one markdown file per source with real frontmatter
   (`url`, `title`, `query`, `fetched_at`) and either the full page content
   or a binary-source stub. (Verified 2026-09-28: confirmed via a direct
   unit test of `vault.archive_sources` with both a normal HTML source and a
   `.pdf`-extension source - the PDF correctly got stubbed instead of
   mangled.)
2. **Vault-as-context surfaces prior work.** Ask about a topic adjacent to
   an existing note (e.g. "context engineering and RAG" after already having
   a RAG report) and confirm the retrieved context names the right prior
   note. (Verified 2026-09-28: asking about "context engineering" correctly
   surfaced the earlier "What is retrieval augmented generation?" report as
   the top match, with the right title and filename.)
3. **Profile evolves and is append-only.** After a run, `Profile.md`'s
   `## Session Log` should have a new dated entry, and `## Standing
   Preferences` should be byte-for-byte unchanged. (Verified 2026-09-28: ran
   a full "What is MCP?" research session - the Session Log gained a dated
   entry with real bullets about the session's topic and jargon, and the
   Standing Preferences section was untouched.)

**What "good" looks like**: a third run on a related topic should visibly
reference the first two (either in the generated search query or the
summary's phrasing), and its profile-update entry should build on, not
repeat, the earlier ones. What would indicate a real problem: the profile
entries becoming generic/repetitive regardless of topic (prompt not
actually using the profile), or vault context always coming back empty even
when clearly-related prior notes exist (retrieval broken).

**Known limitation**: even with `ddgs` (see `DECISIONS.md`), the underlying
free HTML-scraping search backend can occasionally rate-limit and return
zero sources for a run. The pipeline degrades gracefully (a report with no
archived sources for that run, not a crash) rather than failing outright -
not something to chase further without switching to a paid search API.

## Demo script (~2 minutes)

1. **Open the dashboard** (`http://localhost:3001`) - show the history page
   with a couple of existing reports. *"This reads straight from my
   Obsidian vault, not from some database - the vault is the actual
   history."*
2. **Click into a report** - show the `## Key Findings` / `## Open
   Questions` / `## Sources` structure, click a source link to show it
   opens the full archived page content, not just a URL.
3. **Open `Profile.md`** in the dashboard's Profile tab - point at the
   `## Session Log` entries. *"Every time I research something, it writes
   itself a note about what I'm interested in - and I can edit `Standing
   Preferences` myself, it never touches that part."*
4. **Start a new research topic** related to an existing note (e.g. if you
   have a report on RAG, ask about "vector databases for RAG"). Watch the
   live status update (current query, loop count) as it streams.
5. **When it finishes**: point out the Windows toast notification, click it
   to jump straight to the new report - then open the report and show it
   explicitly references or builds on the earlier RAG note, instead of
   starting from scratch.
6. **Try a comparison** (e.g. "Compare PostgreSQL vs MongoDB vs Redis for
   analytics workloads") with the Debate mode checkbox on. *"It detected
   this is a comparison and researched all three in parallel - not
   sequentially - and this Perspectives section is a second, genuinely
   different model arguing against the summary, running concurrently on the
   CPU while the main model runs on GPU."*
7. **Open the Knowledge Graph tab** - show the notes clustering by topic
   similarity. *"This is the same retrieval it uses to build on prior
   research, just visualized."*
8. **Close with the "why"**: *"Same iterative research loop as the open-
   source tutorial this is forked from, but instead of a one-off answer, it
   builds a permanent, linked, personalized knowledge base - compares things
   in parallel instead of one at a time, argues with itself when useful, and
   starts automatically when I log in, so it's just always there."*
