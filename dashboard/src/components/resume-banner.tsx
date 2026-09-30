"use client";

import { RotateCcw } from "lucide-react";

/** Shown when the page is displaying a remembered run (the user left and came back, or it finished).
 * Starting something new needs an explicit click so a finished thread is never reused for another goal. */
export function ResumeBanner({
  loading,
  noun,
  onReset,
}: {
  loading: boolean;
  noun: string;
  onReset: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-surface px-4 py-3 text-sm">
      <span className="text-muted">
        {loading
          ? `A ${noun} is running. It keeps going if you leave this page; come back here any time to see it.`
          : `Showing your last ${noun}.`}
      </span>
      <button
        type="button"
        onClick={onReset}
        className="flex items-center gap-1.5 rounded-full border border-border px-3.5 py-1.5 text-xs font-medium transition-colors hover:border-accent/40 hover:text-accent"
      >
        <RotateCcw className="h-3.5 w-3.5" />
        {loading ? `Leave it and start a new ${noun}` : `Start a new ${noun}`}
      </button>
    </div>
  );
}
