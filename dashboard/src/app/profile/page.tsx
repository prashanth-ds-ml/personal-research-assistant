import ReactMarkdown from "react-markdown";
import { UserCog } from "lucide-react";
import { readProfileNote } from "@/lib/vault";

export const dynamic = "force-dynamic";

export default async function ProfilePage() {
  const content = await readProfileNote();

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Profile</h1>
        <p className="mt-1 text-sm text-muted">
          Read-only view of <code className="rounded bg-surface-hover px-1 py-0.5 text-xs">Profile.md</code>.
          Edit &quot;Standing Preferences&quot; yourself in Obsidian - the assistant only ever
          appends to &quot;Session Log&quot;.
        </p>
      </div>
      <div className="flex items-start gap-3 rounded-2xl border border-border bg-surface p-6 shadow-sm">
        <span className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent-soft text-accent">
          <UserCog className="h-4 w-4" />
        </span>
        <div className="prose prose-sm dark:prose-invert max-w-none flex-1">
          <ReactMarkdown>{content}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}
