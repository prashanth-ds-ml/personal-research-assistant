import Link from "next/link";
import { getResearchNote, listResearchNotes, type ResearchNote } from "@/lib/vault";
import { parseReport } from "@/lib/report";
import { compareIssues, sameTopic, type IssueFacts } from "@/lib/compare";

export const dynamic = "force-dynamic";

type Params = { [key: string]: string | string[] | undefined };
const first = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";

const facts = (n: ResearchNote): IssueFacts => ({
  title: n.title,
  goal: n.goal,
  date: n.date,
  words: n.words,
  facts: n.evidence,
  sources: n.sourcesCount,
  report: parseReport(n.content, n.title),
});

export default async function ComparePage({ searchParams }: { searchParams: Promise<Params> }) {
  const params = await searchParams;
  const deep = (await listResearchNotes()).filter((n) => n.kind === "deep-research");

  // Default: the two newest issues that answer the same question, else the two newest.
  let defA = deep[1]?.slug ?? "";
  let defB = deep[0]?.slug ?? "";
  outer: for (let i = 0; i < deep.length; i++) {
    for (let j = i + 1; j < deep.length; j++) {
      if (sameTopic(deep[i], deep[j])) {
        defB = deep[i].slug;
        defA = deep[j].slug;
        break outer;
      }
    }
  }
  const slugA = first(params.a) || defA;
  const slugB = first(params.b) || defB;
  const [noteA, noteB] = await Promise.all([slugA ? getResearchNote(slugA) : null, slugB ? getResearchNote(slugB) : null]);

  const pick = (side: "a" | "b", current: string) => {
    const other = side === "a" ? slugB : slugA;
    return deep.map((n) => {
      const sp = new URLSearchParams({ a: side === "a" ? n.slug : slugA, b: side === "b" ? n.slug : slugB });
      return (
        <Link
          key={n.slug}
          href={`/compare?${sp.toString()}`}
          className={`block border px-4 py-3 text-sm ${n.slug === current ? "border-accent bg-accent-soft" : "border-border bg-surface hover:border-accent"} ${n.slug === other ? "opacity-60" : ""}`}
        >
          <span className="font-semibold">{n.title}</span>
          <span className="block text-xs text-muted">
            {n.date} · {n.evidence} facts · {n.sourcesCount} sources
          </span>
        </Link>
      );
    });
  };

  const a = noteA ? facts(noteA) : null;
  const b = noteB ? facts(noteB) : null;
  const same = a && b ? sameTopic(a, b) : false;
  const cmp = a && b && noteA?.slug !== noteB?.slug ? compareIssues(a, b) : null;
  const maxFacts = cmp ? Math.max(1, ...cmp.chapters.map((c) => Math.max(c.before ?? 0, c.after ?? 0))) : 1;
  const delta = (x: number, y: number) => (y === x ? "no change" : `${y > x ? "+" : "−"}${Math.abs(y - x)}`);

  return (
    <div className="flex flex-col gap-10">
      <div>
        <div className="kicker">Compare issues</div>
        <h1 className="mt-1 max-w-3xl text-5xl leading-[1.05]">What changed after you added more reading?</h1>
        <p className="mt-3 max-w-2xl text-sm text-muted">
          Pick two issues. When they answer the same question, you see which chapters gained evidence, whether the recommendation moved, and which sources arrived.
        </p>
      </div>

      {deep.length < 2 ? (
        <div className="max-w-xl py-6">
          <div className="font-serif text-4xl leading-tight">Two issues are needed.</div>
          <p className="mt-3 font-serif text-xl italic text-muted">Run a deep research at least twice, ideally the same goal before and after collecting more sources.</p>
          <Link href="/deep" className="mt-5 inline-block rounded bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground">
            Start a deep research
          </Link>
        </div>
      ) : (
        <>
          <div className="grid gap-6 md:grid-cols-[1fr_auto_1fr] md:items-start">
            <div className="space-y-2">
              <div className="kicker text-muted">Earlier issue</div>
              {pick("a", slugA)}
            </div>
            <div className="hidden pt-8 font-serif text-5xl text-accent md:block">→</div>
            <div className="space-y-2">
              <div className="kicker text-muted">Newer issue</div>
              {pick("b", slugB)}
            </div>
          </div>

          {a && b && !cmp && <p className="font-serif text-xl italic text-muted">Pick two different issues.</p>}

          {cmp && a && b && (
            <>
              {!same && (
                <div className="border border-dashed border-accent bg-accent-soft px-5 py-4 text-sm">
                  These two issues look like they are about different questions, so chapter-by-chapter differences may mean little. The numbers are still real.
                </div>
              )}
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
                {cmp.stats.map((s) => (
                  <div key={s.label} className="border-t-[3px] border-t-foreground pt-3">
                    <div className="text-[11px] font-semibold uppercase tracking-widest text-muted">{s.label}</div>
                    <div className="mt-1 flex items-baseline gap-3">
                      <span className="font-serif text-3xl text-muted">{s.before}</span>
                      <span className="text-accent">→</span>
                      <span className="font-serif text-6xl leading-none">{s.after}</span>
                    </div>
                    <span className="mt-2 inline-block rounded-[3px] bg-surface-hover px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider">{delta(s.before, s.after)}</span>
                  </div>
                ))}
              </div>

              <div className="grid gap-12 lg:grid-cols-[1.3fr_1fr]">
                <div>
                  <h2 className="mb-2 text-3xl">Evidence, chapter by chapter</h2>
                  {cmp.chapters.length === 0 && <p className="text-sm text-muted">These notes have no evidence tables to compare.</p>}
                  {cmp.chapters.map((c) => (
                    <div key={c.title} className="grid grid-cols-[minmax(0,1fr)_130px_130px_90px] items-center gap-4 border-t border-border py-3">
                      <span className="font-serif text-lg leading-snug">{c.title}</span>
                      <span className="h-2.5 rounded-[2px] bg-border">
                        <span className="block h-2.5 rounded-[2px] bg-muted" style={{ width: `${((c.before ?? 0) / maxFacts) * 100}%` }} />
                      </span>
                      <span className="h-2.5 rounded-[2px] bg-border">
                        <span className={`block h-2.5 rounded-[2px] ${(c.after ?? 0) === 0 ? "bg-accent" : "bg-success"}`} style={{ width: `${((c.after ?? 0) / maxFacts) * 100}%` }} />
                      </span>
                      <span className="text-center text-xs font-semibold text-muted">
                        {c.change === "new" ? "new chapter" : c.change === "dropped" ? "dropped" : c.change === "same" ? "same" : delta(c.before ?? 0, c.after ?? 0) + " facts"}
                      </span>
                    </div>
                  ))}
                  <div className="mt-1 grid grid-cols-[minmax(0,1fr)_130px_130px_90px] gap-4 text-xs text-muted">
                    <span />
                    <span>earlier</span>
                    <span>newer</span>
                    <span />
                  </div>
                </div>

                <div>
                  <h2 className="mb-3 text-3xl">Did the recommendation move?</h2>
                  {cmp.recommendation ? (
                    <div className="space-y-3">
                      <div className="border border-l-[4px] border-border border-l-muted bg-surface p-5">
                        <div className="kicker text-muted">Earlier</div>
                        <p className="mt-1 font-serif text-xl italic leading-snug">{cmp.recommendation.before}</p>
                      </div>
                      <div className="text-center font-serif text-2xl text-accent">{cmp.recommendation.changed ? "↓ changed" : "↓ the same"}</div>
                      <div className="border border-l-[4px] border-border border-l-accent bg-surface p-5">
                        <div className="kicker text-muted">Newer</div>
                        <p className="mt-1 font-serif text-xl italic leading-snug">{cmp.recommendation.after}</p>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-muted">One of the issues has no written recommendations chapter, so there is nothing to compare.</p>
                  )}
                </div>
              </div>

              <div className="grid gap-12 md:grid-cols-2">
                <div>
                  <h2 className="mb-2 text-2xl">Sources added</h2>
                  {cmp.addedSources.length === 0 && <p className="text-sm text-muted">None.</p>}
                  {cmp.addedSources.slice(0, 12).map((t) => (
                    <div key={t} className="border-t border-border py-2.5 font-serif text-lg leading-snug">
                      <span className="mr-2 font-sans font-bold text-success">+</span>
                      {t}
                    </div>
                  ))}
                </div>
                <div>
                  <h2 className="mb-2 text-2xl">No longer used</h2>
                  {cmp.droppedSources.length === 0 && <p className="text-sm text-muted">None.</p>}
                  {cmp.droppedSources.slice(0, 12).map((t) => (
                    <div key={t} className="border-t border-border py-2.5 font-serif text-lg leading-snug">
                      <span className="mr-2 font-sans font-bold text-danger">−</span>
                      {t}
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex gap-3">
                <Link href={`/research/${noteB?.slug}`} className="rounded bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground">
                  Read the newer issue
                </Link>
                <Link href={`/research/${noteA?.slug}`} className="rounded border border-foreground px-4 py-2 text-sm font-semibold">
                  Read the earlier issue
                </Link>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
