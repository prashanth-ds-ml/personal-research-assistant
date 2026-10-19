import path from "node:path";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ArrowLeft, Calendar, Layers, Link2, RefreshCw } from "lucide-react";
import { SafeMarkdown } from "@/components/safe-markdown";
import { getResearchNote } from "@/lib/vault";
import { findTraceForTopic } from "@/lib/langsmith";
import { parseReport } from "@/lib/report";
import { StatusBadge } from "@/components/status-badge";
import { TraceCard } from "@/components/trace-card";
import { FeedbackBar } from "@/components/feedback-bar";
import { MagazineReader } from "@/components/magazine-reader";

export const dynamic = "force-dynamic";

/** The LangSmith lookup is a network call that can be slow or fail; it must never hold up the report. */
async function Trace({ title }: { title: string }) {
  const trace = await findTraceForTopic(title);
  return trace ? <TraceCard trace={trace} /> : null;
}

export default async function ResearchNotePage({ params }: PageProps<"/research/[slug]">) {
  const { slug } = await params;
  const note = await getResearchNote(slug);
  if (!note) notFound();

  // A goal-driven (deep) report is laid out as a magazine. Quick notes, and anything the parser cannot make
  // chapters out of, keep the plain reading view.
  const report = note.kind === "deep-research" ? parseReport(note.content, note.title) : null;
  if (report && report.chapters.length > 0) {
    const vault = path.basename(process.env.VAULT_PATH ?? "") || "Research";
    const sub = process.env.RESEARCH_SUBDIR ?? "Research";
    return (
      <MagazineReader
        report={report}
        meta={{
          slug: note.slug,
          title: note.title,
          date: note.date,
          words: note.words,
          facts: note.evidence,
          sourcesCount: note.sourcesCount,
          obsidianUrl: `obsidian://open?vault=${encodeURIComponent(vault)}&file=${encodeURIComponent(`${sub}/${note.slug}`)}`,
        }}
      >
        <FeedbackBar slug={note.slug} initialRating={note.feedbackRating} initialNote={note.feedbackNote} />
      </MagazineReader>
    );
  }

  return (
    <article className="mx-auto flex max-w-3xl flex-col gap-6">
      <Link href="/reports" className="flex w-fit items-center gap-1.5 text-sm text-muted hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to reports
      </Link>

      <div className="flex flex-col gap-3 border-b border-border pb-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-4xl leading-tight">{note.title}</h1>
            <StatusBadge status={note.status} />
          </div>
          <Link
            href={`/new?topic=${encodeURIComponent(note.title)}`}
            className="flex shrink-0 items-center gap-1.5 rounded border border-border px-3 py-1.5 text-xs font-semibold text-muted hover:border-accent hover:text-accent"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Continue researching this topic
          </Link>
        </div>
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
          <span className="flex items-center gap-1">
            <Calendar className="h-3.5 w-3.5" />
            {note.date}
          </span>
          <span className="flex items-center gap-1">
            <Layers className="h-3.5 w-3.5" />
            {note.loops} loops
          </span>
          <span className="flex items-center gap-1">
            <Link2 className="h-3.5 w-3.5" />
            {note.sourcesCount} sources
          </span>
        </div>
      </div>

      <Suspense fallback={null}>
        <Trace title={note.title} />
      </Suspense>

      <div className="prose prose-zinc max-w-none font-serif dark:prose-invert prose-headings:font-serif prose-p:text-[1.1rem] prose-p:leading-8">
        <SafeMarkdown>{note.content}</SafeMarkdown>
      </div>

      <FeedbackBar slug={note.slug} initialRating={note.feedbackRating} initialNote={note.feedbackNote} />
    </article>
  );
}
