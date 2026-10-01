import Link from "next/link";
import { RunsList } from "@/components/runs-list";

export const dynamic = "force-dynamic";

export default function RunsPage() {
  return (
    <div className="flex flex-col gap-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Runs</h1>
          <p className="mt-1 text-sm text-muted">
            Every deep-research run, including ones still going or that never finished. Open one to watch what it is doing.
          </p>
        </div>
        <Link
          href="/deep"
          className="shrink-0 rounded-full bg-accent px-4 py-2 text-sm font-medium text-accent-foreground shadow-sm shadow-accent/30 transition-transform hover:scale-[1.03] active:scale-[0.98]"
        >
          New deep research
        </Link>
      </div>
      <RunsList />
    </div>
  );
}
