"use client";

import { useState } from "react";

const DOWN = /fetch|network|ECONN|refused|502|503|504|unreachable|Load failed|timed? ?out|socket/i;

/** A failure explained like a person would: what is wrong, what to do, and a button to try again. */
export function ErrorCard({ error, onRetry, context = "the research engine" }: { error: unknown; onRetry?: () => void; context?: string }) {
  const [open, setOpen] = useState(false);
  const text = error instanceof Error ? error.message : String(error ?? "");
  const down = DOWN.test(text);
  return (
    <div role="alert" className="border border-l-4 border-danger bg-danger-soft px-5 py-4">
      <div className="font-serif text-2xl leading-snug">{down ? `It can't reach ${context}.` : "Something went wrong."}</div>
      <p className="mt-1 text-sm leading-relaxed">
        {down ? (
          <>
            The research engine is probably not running. Start it in a terminal with{" "}
            <code className="rounded bg-surface px-1.5 py-0.5 text-[13px]">langgraph dev</code>, then try again. Nothing you did is lost: a run in progress keeps its place.
          </>
        ) : (
          "The page could not finish what you asked. Try again; if it keeps happening, the details below say why."
        )}
      </p>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button type="button" onClick={onRetry ?? (() => window.location.reload())} className="rounded bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground hover:opacity-90">
          Try again
        </button>
        {text && (
          <button type="button" onClick={() => setOpen((v) => !v)} className="text-sm font-semibold underline">
            {open ? "Hide details" : "Show details"}
          </button>
        )}
      </div>
      {open && <pre className="mt-3 max-h-40 overflow-auto whitespace-pre-wrap rounded border border-border bg-surface p-3 text-xs">{text}</pre>}
    </div>
  );
}
