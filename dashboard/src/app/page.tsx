import Link from "next/link";
import { listResearchNotes } from "@/lib/vault";
import { listRuns } from "@/lib/runs";
import { listLibrary } from "@/lib/library";
import { systemStatus, EXPECTED_MODELS, WANT_FREE_GB } from "@/lib/system";
import { parseReport } from "@/lib/report";
import { CoverArt } from "@/components/cover-art";
import { BriefBox } from "@/components/brief-box";
import { FreeMemoryButton } from "@/components/free-memory-button";
import { ago, isActive, progressText } from "@/components/run-status";

// The front page reads the vault, the run records and the local machine fresh every time.
export const dynamic = "force-dynamic";

function greeting(): string {
  const h = new Date().getHours();
  return h < 12 ? "Good morning." : h < 18 ? "Good afternoon." : "Good evening.";
}

export default async function FrontPage() {
  const [notes, runs, library, sys] = await Promise.all([listResearchNotes(), listRuns(), listLibrary(), systemStatus()]);
  const deep = notes.filter((n) => n.kind === "deep-research");
  const latest = deep[0];
  const recent = deep.slice(1, 4);
  const seenGoals = new Set<string>();
  // one card per goal: the same goal started twice should not appear twice (runs are newest first)
  const active = runs
    .filter((r) => isActive(r.status))
    .filter((r) => {
      const key = r.goal.trim().toLowerCase();
      if (seenGoals.has(key)) return false;
      seenGoals.add(key);
      return true;
    })
    .slice(0, 2);
  // the "nothing on the desk" welcome is for a truly empty install; with a library but no reports yet, the brief box comes first
  const firstRun = notes.length === 0 && runs.length === 0 && library.length === 0;

  // Run records include the time a run sat waiting for you, so a measured average would mislead. This is the range seen
  // on this machine (a 41 minute run was typical); sources collected from the web add to it.
  const estimate = "Plan 30 to 60 minutes";

  const missing = EXPECTED_MODELS.filter((m) => !sys.installed.includes(m));
  const ready: { ok: boolean; text: string }[] = [
    { ok: sys.engine, text: sys.engine ? "The research engine is running" : "The research engine is not running. Start it with: langgraph dev" },
    sys.ollama
      ? { ok: missing.length === 0, text: missing.length === 0 ? `Ollama running, ${EXPECTED_MODELS.length} models installed` : `Ollama running, but not installed: ${missing.join(", ")}` }
      : { ok: false, text: "Ollama is not running. Start it, then reload." },
    { ok: library.length > 0, text: library.length > 0 ? `Library holds ${library.length} documents` : "The library is empty; the collector will search the web first" },
    { ok: sys.enoughMemory, text: `Memory: ${sys.freeGb} GB free. Long runs want about ${WANT_FREE_GB} GB` },
  ];

  // Ideas come from the latest issue's own gaps, so they are questions the library genuinely could not answer.
  const report = latest ? parseReport(latest.content, latest.title) : null;
  const ideas = (report?.chapters ?? [])
    .filter((c) => c.kind !== "ok" || (c.facts !== null && c.facts < 3))
    .slice(0, 3)
    .map((c) => ({
      title: c.title,
      why: c.kind === "gap" ? "The latest issue had no evidence for this chapter." : c.kind === "failed" ? "The model could not write this chapter last time." : "The latest issue found only thin evidence here.",
      href: `/deep?goal=${encodeURIComponent(`${latest?.goal || latest?.title || ""} — focus on: ${c.title}`)}`,
    }));

  if (firstRun) {
    return (
      <div className="grid gap-12 py-10 md:grid-cols-[1.2fr_1fr] md:items-center">
        <div>
          <div className="kicker">Front page</div>
          <h1 className="mt-3 text-5xl leading-none sm:text-7xl">Nothing on the desk yet.</h1>
          <p className="mt-5 max-w-xl font-serif text-2xl italic leading-relaxed text-muted">Three small steps and your first issue is on the press. Everything runs on this machine.</p>
          <div className="mt-8 flex gap-3">
            <Link href="/library" className="rounded bg-accent px-5 py-3 text-sm font-semibold text-accent-foreground">
              Look at the library
            </Link>
            <Link href="/deep" className="rounded border border-foreground px-5 py-3 text-sm font-semibold">
              Ask a question
            </Link>
          </div>
        </div>
        <div>
          {[
            ["1", "Add a few sources", "Drop PDFs into the Library folder, or let the collector find some."],
            ["2", "Ask a question", "One sentence is enough. It asks three short questions back."],
            ["3", "Read your first issue", "A magazine-style report where every claim shows its evidence."],
          ].map(([n, t, d]) => (
            <div key={n} className="flex gap-5 border-t border-border py-5">
              <span className="font-serif text-5xl leading-none text-accent">{n}</span>
              <div>
                <div className="font-serif text-2xl">{t}</div>
                <div className="mt-1 text-sm text-muted">{d}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // when a run is working or waiting, it is what you came back for: it leads the page and the brief box shrinks
  const busy = active.length > 0;
  const continueSection = busy ? (
        <section>
          <div className="kicker">Continue where you left off</div>
          <div className="mt-3 grid gap-5 md:grid-cols-2">
            {active.map((r) => {
              const pct = r.progress.questions_total ? Math.round(((r.progress.questions_done ?? 0) / r.progress.questions_total) * 100) : 0;
              return (
                <Link key={r.id} href={`/runs/${r.id}`} className="group border border-border border-t-4 border-t-foreground bg-surface p-5 transition-all hover:-translate-y-0.5 hover:shadow-lg">
                  <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-widest">
                    <span className={r.status === "waiting" ? "text-warning" : "text-info"}>{r.status === "waiting" ? "Waiting for you" : "Running"}</span>
                    <span className="flex-1" />
                    <span className="font-normal normal-case tracking-normal text-muted">{ago(r.updatedAt)}</span>
                  </div>
                  <div className="mt-2 font-serif text-2xl leading-snug group-hover:text-accent">{r.goal.split("\n")[0].slice(0, 140) || "(no goal recorded)"}</div>
                  {r.status === "waiting" ? (
                    <div className="mt-3 text-sm font-semibold text-accent">
                      {r.waitingFor === "clarify" ? "Answer its questions" : r.waitingFor === "review" ? "Choose the sources" : "Approve the plan"} →
                    </div>
                  ) : (
                    <>
                      <div className="mt-4 h-2 rounded-[2px] bg-border">
                        <div className="h-2 rounded-[2px] bg-accent" style={{ width: `${pct}%` }} />
                      </div>
                      <div className="mt-2 text-xs text-muted">{progressText(r.progress) || r.step || "starting"}</div>
                    </>
                  )}
                </Link>
              );
            })}
          </div>
        </section>
  ) : null;

  return (
    <div className="flex flex-col gap-12">
      <div className="flex flex-wrap gap-x-5 text-xs font-semibold uppercase tracking-[0.14em] text-muted">
        <span className="text-accent">Front page</span>
        <span>{new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</span>
        <span>Issue {deep.length}</span>
      </div>

      {continueSection}

      <div className="grid gap-12 lg:grid-cols-[1.7fr_1fr]">
        <div>
          <h1 className={busy ? "text-3xl leading-tight sm:text-4xl" : "text-5xl leading-none sm:text-7xl"}>
            {greeting()}
            <br />
            <span className="text-muted">What shall we look into?</span>
          </h1>
          <div className={busy ? "mt-4" : "mt-8"}>
            <BriefBox compact={busy} />
          </div>
        </div>

        <aside className="self-start border border-border border-t-4 border-t-accent bg-surface p-6">
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Before you begin</div>
          <div className="mt-2 font-serif text-3xl leading-tight">{estimate}</div>
          <div className="mt-4">
            {ready.map((r) => (
              <div key={r.text} className="flex gap-3 border-t border-border py-2.5 text-sm leading-snug">
                <span className={`mt-0.5 text-[11px] ${r.ok ? "text-success" : "text-warning"}`} aria-hidden>
                  ●
                </span>
                <span>{r.text}</span>
              </div>
            ))}
          </div>
          {sys.ollama && !sys.enoughMemory && <FreeMemoryButton loaded={sys.loaded} />}
          {sys.ollama && sys.enoughMemory && <div className="mt-3 text-sm font-semibold text-success">Ready. Enough memory for the writer.</div>}
        </aside>
      </div>

      {!latest && (
        <section className="border border-dashed border-border px-8 py-10">
          <div className="kicker">Latest issue</div>
          <div className="mt-2 font-serif text-4xl leading-tight">Your first issue will appear here.</div>
          <p className="mt-2 max-w-xl font-serif text-xl italic text-muted">Ask a question above. When the report is written it shows up as a cover, with the evidence behind every claim.</p>
        </section>
      )}

      {latest && (
        <section className="relative overflow-hidden bg-ink text-ink-foreground">
          <div className="absolute inset-y-0 left-0 w-2 bg-accent" />
          <div className="grid gap-8 md:grid-cols-[1.3fr_1fr]">
            <div className="p-8 pl-10 sm:p-10 sm:pl-12">
              <div className="text-xs font-semibold uppercase tracking-[0.14em] text-[#ff7a5e]">Latest issue · {latest.date}</div>
              <div className="mt-3 font-serif text-4xl font-medium leading-[1.05] tracking-tight sm:text-5xl">{latest.title}</div>
              <p className="mt-4 font-serif text-xl italic leading-relaxed text-[#c9d4e3]">
                {report && report.chapters.length > 0
                  ? `${report.chapters.filter((c) => c.kind === "ok").length} of ${report.chapters.length} chapters written. ${latest.evidence} verified facts from ${latest.sourcesCount} sources.`
                  : `${latest.evidence} verified facts from ${latest.sourcesCount} sources.`}
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <Link href={`/research/${latest.slug}`} className="rounded bg-accent px-5 py-3 text-sm font-semibold text-accent-foreground">
                  Read the issue →
                </Link>
                {deep.length > 1 && (
                  <Link href="/compare" className="rounded border border-[#5b7090] px-5 py-3 text-sm font-semibold hover:border-white">
                    Compare with an earlier issue
                  </Link>
                )}
              </div>
            </div>
            <CoverArt seed={latest.slug} facts={latest.evidence} hero className="hidden h-full min-h-72 w-full md:block" />
          </div>
        </section>
      )}

      <div className="grid gap-12 lg:grid-cols-[1fr_1.2fr]">
        <section>
          <div className="kicker">Ideas from your library</div>
          <h2 className="mb-2 mt-2 text-3xl leading-tight">Questions the latest issue could not answer</h2>
          {ideas.length === 0 ? (
            <p className="border-t border-border py-4 font-serif text-lg italic text-muted">No gaps in the latest issue. Ask something new.</p>
          ) : (
            ideas.map((i, n) => (
              <Link key={i.title} href={i.href} className="group flex gap-4 border-t border-border py-4">
                <span className="font-serif text-4xl leading-none text-accent">{n + 1}</span>
                <span>
                  <span className="block font-serif text-xl leading-snug group-hover:text-accent">{i.title}</span>
                  <span className="text-sm text-muted">{i.why}</span>
                </span>
              </Link>
            ))
          )}
        </section>

        <section>
          <div className="kicker">Recent issues</div>
          {recent.length === 0 ? (
            <p className="mt-3 border-t border-border py-4 font-serif text-lg italic text-muted">
              Your earlier issues will appear here.{" "}
              <Link href="/deep" className="font-sans text-sm font-semibold not-italic text-accent hover:underline">
                Start the first one →
              </Link>
            </p>
          ) : (
            <div className="mt-3 grid grid-cols-3 gap-4">
              {recent.map((n) => (
                <Link key={n.slug} href={`/research/${n.slug}`} className="group flex flex-col overflow-hidden border border-border bg-surface transition-all hover:-translate-y-0.5 hover:shadow-lg">
                  <CoverArt seed={n.slug} facts={n.evidence} className="h-24 w-full bg-background" />
                  <span className="p-3">
                    <span className="block font-serif text-lg leading-snug group-hover:text-accent">{n.title}</span>
                    <span className="mt-1 block text-xs text-muted">
                      {n.date} · {n.evidence} facts
                    </span>
                  </span>
                </Link>
              ))}
            </div>
          )}
          <Link href="/reports" className="mt-4 inline-block text-sm font-semibold text-accent hover:underline">
            All reports →
          </Link>
        </section>
      </div>
    </div>
  );
}
