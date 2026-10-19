import Link from "next/link";
import { listResearchNotes } from "@/lib/vault";
import { CoverArt } from "@/components/cover-art";
import { StatusBadge } from "@/components/status-badge";

// Always read the vault fresh - this page must never serve a stale, build-time snapshot of the reports.
export const dynamic = "force-dynamic";

type Filter = "all" | "deep" | "quick";
type Params = { [key: string]: string | string[] | undefined };

const first = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? "";

export default async function ReportsPage({ searchParams }: { searchParams: Promise<Params> }) {
  const params = await searchParams;
  const kind = first(params.kind);
  const filter: Filter = kind === "deep" || kind === "quick" ? kind : "all";
  const q = first(params.q).trim();
  const all = await listResearchNotes();
  const deep = all.filter((n) => n.kind === "deep-research");
  const quick = all.filter((n) => n.kind !== "deep-research");
  const pool = filter === "deep" ? deep : filter === "quick" ? quick : all;
  const notes = q ? pool.filter((n) => n.title.toLowerCase().includes(q.toLowerCase())) : pool;

  const tabs: { key: Filter; label: string; count: number }[] = [
    { key: "all", label: "All", count: all.length },
    { key: "deep", label: "Deep research", count: deep.length },
    { key: "quick", label: "Quick research", count: quick.length },
  ];
  const href = (key: Filter) => {
    const sp = new URLSearchParams();
    if (key !== "all") sp.set("kind", key);
    if (q) sp.set("q", q);
    const s = sp.toString();
    return s ? `/reports?${s}` : "/reports";
  };

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="kicker">The newsstand</div>
          <h1 className="mt-1 text-5xl leading-none">Reports</h1>
          <p className="mt-3 max-w-xl text-sm text-muted">
            Finished issues, read straight from your Obsidian vault. Runs that are still going, or never finished, are under{" "}
            <Link href="/runs" className="font-medium text-accent hover:underline">
              Runs
            </Link>
            .
          </p>
        </div>
        <div className="flex gap-3">
          <Link href="/compare" className="rounded border border-foreground px-4 py-2 text-sm font-semibold hover:bg-foreground hover:text-background">
            Compare two issues
          </Link>
          <Link href="/deep" className="rounded bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground hover:opacity-90">
            New deep research
          </Link>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <form action="/reports" className="flex">
          {filter !== "all" && <input type="hidden" name="kind" value={filter} />}
          <input
            name="q"
            defaultValue={q}
            aria-label="Search issues"
            placeholder="Search issues"
            className="w-56 rounded border border-border bg-surface px-3 py-1.5 text-sm outline-none focus:border-accent"
          />
        </form>
        <nav aria-label="Report type" className="flex flex-wrap gap-2">
          {tabs.map((t) => (
            <Link
              key={t.key}
              href={href(t.key)}
              aria-current={filter === t.key ? "page" : undefined}
              className={`rounded px-3 py-1.5 text-xs font-semibold transition-colors ${
                filter === t.key ? "bg-accent-soft text-accent" : "border border-border text-muted hover:text-foreground"
              }`}
            >
              {t.label} ({t.count})
            </Link>
          ))}
        </nav>
      </div>

      {notes.length === 0 ? (
        <div className="max-w-xl py-10">
          <div className="font-serif text-5xl leading-none tracking-tight">{q ? "No issue matches." : "Nothing on the stand yet."}</div>
          <p className="mt-4 font-serif text-xl italic text-muted">
            {q ? "Try fewer words, or ask the desk to research it." : "Your first deep-research report will appear here as an issue."}
          </p>
          <div className="mt-6 flex gap-3">
            <Link href="/deep" className="rounded bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground">
              Start a deep research
            </Link>
            {q && (
              <Link href="/reports" className="rounded border border-foreground px-4 py-2 text-sm font-semibold">
                Clear the search
              </Link>
            )}
          </div>
        </div>
      ) : (
        <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {notes.map((note) => {
            const isDeep = note.kind === "deep-research";
            return (
              <li key={note.slug}>
                <Link
                  href={`/research/${note.slug}`}
                  className={`group flex h-full flex-col overflow-hidden border border-border border-t-8 bg-surface transition-all hover:-translate-y-0.5 hover:shadow-lg ${
                    isDeep ? "border-t-accent" : "border-t-foreground"
                  }`}
                >
                  <CoverArt seed={note.slug} facts={isDeep ? note.evidence : note.loops * 4} className="h-28 w-full bg-background" />
                  <div className="flex flex-1 flex-col gap-3 p-5">
                    <div className="flex items-center gap-2 text-xs">
                      <span className={`rounded px-2 py-0.5 text-[11px] font-semibold ${isDeep ? "bg-accent-soft text-accent" : "bg-surface-hover text-muted"}`}>
                        {isDeep ? "Deep" : "Quick"}
                      </span>
                      <span className="text-muted">{note.date}</span>
                      <StatusBadge status={note.status} />
                    </div>
                    <span className="font-serif text-2xl leading-tight tracking-tight group-hover:text-accent">{note.title}</span>
                    <span className="mt-auto text-xs text-muted">
                      {isDeep
                        ? `${note.words.toLocaleString()} words · ${note.evidence} verified facts · ${note.sourcesCount} source${note.sourcesCount === 1 ? "" : "s"}`
                        : `${note.loops} loop${note.loops === 1 ? "" : "s"} · ${note.sourcesCount} source${note.sourcesCount === 1 ? "" : "s"}`}
                      {note.feedbackRating ? ` · ${note.feedbackRating === "up" ? "rated helpful" : "rated not helpful"}` : ""}
                    </span>
                  </div>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
