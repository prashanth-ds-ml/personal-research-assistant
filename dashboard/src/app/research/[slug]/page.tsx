import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowLeft, Calendar, Layers, Link2, RefreshCw } from "lucide-react";
import { SafeMarkdown } from "@/components/safe-markdown";
import { getResearchNote } from "@/lib/vault";
import { findTraceForTopic } from "@/lib/langsmith";
import { StatusBadge } from "@/components/status-badge";
import { TraceCard } from "@/components/trace-card";
import { FeedbackBar } from "@/components/feedback-bar";

export const dynamic = "force-dynamic";

export default async function ResearchNotePage({
  params,
}: PageProps<"/research/[slug]">) {
  const { slug } = await params;
  const note = await getResearchNote(slug);
  if (!note) notFound();

  const trace = await findTraceForTopic(note.title);

  return (
    <article className="flex flex-col gap-6">
      <Link
        href="/"
        className="flex w-fit items-center gap-1.5 text-sm text-muted hover:text-foreground"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Back to history
      </Link>

      <div className="flex flex-col gap-3 border-b border-border pb-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-semibold tracking-tight">{note.title}</h1>
            <StatusBadge status={note.status} />
          </div>
          <Link
            href={`/new?topic=${encodeURIComponent(note.title)}`}
            className="flex shrink-0 items-center gap-1.5 rounded-full border border-border px-3 py-1.5 text-xs font-medium text-muted hover:border-accent/40 hover:text-accent"
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

      {trace && <TraceCard trace={trace} />}

      <div className="prose prose-zinc dark:prose-invert max-w-none">
        <SafeMarkdown>{note.content}</SafeMarkdown>
      </div>

      <FeedbackBar slug={note.slug} initialRating={note.feedbackRating} initialNote={note.feedbackNote} />
    </article>
  );
}
