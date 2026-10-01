import Link from "next/link";
import { FileSearch, Calendar, Layers, Link2, ArrowRight, FileText } from "lucide-react";
import { listResearchNotes } from "@/lib/vault";
import { StatusBadge } from "@/components/status-badge";

// Always read the vault fresh - this page must never serve a stale,
// build-time snapshot of the reports.
export const dynamic = "force-dynamic";

type Filter = "all" | "deep" | "quick";

function filterOf(value: string | string[] | undefined): Filter {
  const v = Array.isArray(value) ? value[0] : value;
  return v === "deep" || v === "quick" ? v : "all";
}

export default async function ReportsPage({ searchParams }: { searchParams: Promise<{ [key: string]: string | string[] | undefined }> }) {
  const filter = filterOf((await searchParams).kind);
  const all = await listResearchNotes();
  const deep = all.filter((n) => n.kind === "deep-research");
  const quick = all.filter((n) => n.kind !== "deep-research");
  const notes = filter === "deep" ? deep : filter === "quick" ? quick : all;

  const tabs: { key: Filter; label: string; count: number; href: string }[] = [
    { key: "all", label: "All", count: all.length, href: "/" },
    { key: "deep", label: "Deep research", count: deep.length, href: "/?kind=deep" },
    { key: "quick", label: "Quick research", count: quick.length, href: "/?kind=quick" },
  ];

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Reports</h1>
          <p className="mt-1 text-sm text-muted">
            Finished reports, read straight from your Obsidian vault. Runs that are still going, or never finished, are
            under{" "}
            <Link href="/runs" className="font-medium text-accent hover:underline">
              Runs
            </Link>
            .
          </p>
        </div>
        <Link
          href="/deep"
          className="shrink-0 rounded-full bg-accent px-4 py-2 text-sm font-medium text-accent-foreground shadow-sm shadow-accent/30 transition-transform hover:scale-[1.03] active:scale-[0.98]"
        >
          New deep research
        </Link>
      </div>

      <nav aria-label="Report type" className="flex flex-wrap gap-2">
        {tabs.map((t) => (
          <Link
            key={t.key}
            href={t.href}
            aria-current={filter === t.key ? "page" : undefined}
            className={`rounded-full px-3.5 py-1.5 text-xs font-medium transition-colors ${
              filter === t.key ? "bg-accent-soft text-accent" : "border border-border text-muted hover:text-foreground"
            }`}
          >
            {t.label} ({t.count})
          </Link>
        ))}
      </nav>

      {notes.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border py-20 text-center">
          <FileSearch className="h-8 w-8 text-muted" />
          <p className="text-sm text-muted">
            {filter === "deep" ? "No deep-research reports yet. " : "Nothing here yet. "}
            <Link href="/deep" className="font-medium text-accent hover:underline">
              Start a deep-research goal
            </Link>
          </p>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {notes.map((note) => {
            const isDeep = note.kind === "deep-research";
            return (
              <li key={note.slug}>
                <Link
                  href={`/research/${note.slug}`}
                  className="group flex items-center justify-between gap-4 rounded-2xl border border-border bg-surface p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-md"
                >
                  <div className="flex min-w-0 flex-col gap-2">
                    <div className="flex items-center gap-2">
                      <span className="truncate font-medium">{note.title}</span>
                      <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${isDeep ? "bg-accent-soft text-accent" : "bg-surface-hover text-muted"}`}>
                        {isDeep ? "Deep" : "Quick"}
                      </span>
                      <StatusBadge status={note.status} />
                    </div>
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3.5 w-3.5" />
                        {note.date}
                      </span>
                      {isDeep ? (
                        <>
                          <span className="flex items-center gap-1">
                            <FileText className="h-3.5 w-3.5" />
                            {note.words.toLocaleString()} words
                          </span>
                          <span className="flex items-center gap-1">
                            <Layers className="h-3.5 w-3.5" />
                            {note.evidence} verified facts
                          </span>
                        </>
                      ) : (
                        <span className="flex items-center gap-1">
                          <Layers className="h-3.5 w-3.5" />
                          {note.loops} loop{note.loops === 1 ? "" : "s"}
                        </span>
                      )}
                      <span className="flex items-center gap-1">
                        <Link2 className="h-3.5 w-3.5" />
                        {note.sourcesCount} source{note.sourcesCount === 1 ? "" : "s"}
                      </span>
                      {note.feedbackRating ? <span>{note.feedbackRating === "up" ? "rated helpful" : "rated not helpful"}</span> : null}
                    </div>
                  </div>
                  <ArrowRight className="h-4 w-4 shrink-0 text-muted transition-transform group-hover:translate-x-1 group-hover:text-accent" />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
