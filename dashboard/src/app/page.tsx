import Link from "next/link";
import { FileSearch, Calendar, Layers, Link2, ArrowRight } from "lucide-react";
import { listResearchNotes } from "@/lib/vault";
import { StatusBadge } from "@/components/status-badge";

// Always read the vault fresh - this page must never serve a stale,
// build-time snapshot of research history.
export const dynamic = "force-dynamic";

export default async function HistoryPage() {
  const notes = await listResearchNotes();

  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Research History</h1>
          <p className="mt-1 text-sm text-muted">
            Read straight from your Obsidian vault - {notes.length} report
            {notes.length === 1 ? "" : "s"} so far.
          </p>
        </div>
        <Link
          href="/new"
          className="shrink-0 rounded-full bg-accent px-4 py-2 text-sm font-medium text-accent-foreground shadow-sm shadow-accent/30 transition-transform hover:scale-[1.03] active:scale-[0.98]"
        >
          New Research
        </Link>
      </div>

      {notes.length === 0 ? (
        <div className="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-border py-20 text-center">
          <FileSearch className="h-8 w-8 text-muted" />
          <p className="text-sm text-muted">
            No research yet.{" "}
            <Link href="/new" className="font-medium text-accent hover:underline">
              Start your first topic
            </Link>
          </p>
        </div>
      ) : (
        <ul className="flex flex-col gap-3">
          {notes.map((note) => (
            <li key={note.slug}>
              <Link
                href={`/research/${note.slug}`}
                className="group flex items-center justify-between gap-4 rounded-2xl border border-border bg-surface p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-accent/40 hover:shadow-md"
              >
                <div className="flex min-w-0 flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-medium">{note.title}</span>
                    <StatusBadge status={note.status} />
                  </div>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
                    <span className="flex items-center gap-1">
                      <Calendar className="h-3.5 w-3.5" />
                      {note.date}
                    </span>
                    <span className="flex items-center gap-1">
                      <Layers className="h-3.5 w-3.5" />
                      {note.loops} loop{note.loops === 1 ? "" : "s"}
                    </span>
                    <span className="flex items-center gap-1">
                      <Link2 className="h-3.5 w-3.5" />
                      {note.sourcesCount} source{note.sourcesCount === 1 ? "" : "s"}
                    </span>
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 shrink-0 text-muted transition-transform group-hover:translate-x-1 group-hover:text-accent" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
