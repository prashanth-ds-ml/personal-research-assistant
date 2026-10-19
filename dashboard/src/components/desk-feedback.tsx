"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Flag, ThumbsDown, ThumbsUp } from "lucide-react";
import type { Rating, RunView, Target } from "@/lib/desk";

// Feedback on a report's sources and sentences, saved to the desk database with the run (see lib/desk.ts).
// Every click is one row; clicking the active rating again withdraws it ("cleared").

export interface Desk {
  view: RunView | null;
  error: string;
  current: (target: Target, ref: string) => { rating: Rating; reason: string } | undefined;
  rate: (target: Target, ref: string, rating: Rating, extra?: { reason?: string; section?: string }) => Promise<void>;
}

export function useDesk(runId: string, reportSlug: string): Desk {
  const [view, setView] = useState<RunView | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!runId) return;
    let live = true;
    fetch(`/api/desk/run/${encodeURIComponent(runId)}`)
      .then(async (r) => (r.ok ? ((await r.json()) as RunView) : null))
      .then((v) => live && setView(v))
      .catch(() => live && setView(null));
    return () => {
      live = false;
    };
  }, [runId]);

  const current = useCallback((target: Target, ref: string) => view?.feedback[`${target}|${ref}`], [view]);

  const rate = useCallback(
    async (target: Target, ref: string, rating: Rating, extra?: { reason?: string; section?: string }) => {
      if (!view) return;
      const key = `${target}|${ref}`;
      const before = view.feedback;
      const next = { ...view.feedback };
      if (rating === "cleared") delete next[key];
      else next[key] = { rating, reason: extra?.reason ?? "" };
      setView({ ...view, feedback: next });                       // optimistic; rolled back if the save fails
      setError("");
      try {
        const res = await fetch("/api/desk/feedback", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ runId, reportSlug, target, targetRef: ref, rating, ...extra }),
        });
        if (!res.ok) throw new Error((await res.json()).error ?? `HTTP ${res.status}`);
      } catch (e) {
        setView((v) => (v ? { ...v, feedback: before } : v));
        setError(e instanceof Error ? e.message : "Could not save feedback");
      }
    },
    [view, runId, reportSlug],
  );

  return { view, error, current, rate };
}

const btn = "inline-flex items-center gap-1 rounded border px-2 py-1 text-[11px] font-semibold transition-colors";
const idle = "border-border text-muted hover:border-accent hover:text-accent";

/** 👍 relevant · 👎 not relevant · ⚠ wrong subject, for one cited chunk. */
export function ChunkRating({ desk, eid, section }: { desk: Desk; eid: string; section: string }) {
  if (!desk.view || !desk.view.evidence[eid]) return null;
  const now = desk.current("chunk", eid)?.rating;
  const opts: { rating: Rating; label: string; short: string; icon: React.ReactNode; on: string }[] = [
    { rating: "relevant", label: "Relevant", short: "", icon: <ThumbsUp className="h-3 w-3" />, on: "border-success bg-success-soft text-success" },
    { rating: "not_relevant", label: "Not relevant", short: "", icon: <ThumbsDown className="h-3 w-3" />, on: "border-danger bg-danger-soft text-danger" },
    { rating: "wrong_subject", label: "Wrong subject", short: "Wrong subject", icon: <AlertTriangle className="h-3 w-3" />, on: "border-warning bg-warning-soft text-warning" },
  ];
  return (
    <div className="no-print mt-1.5 flex flex-wrap items-center gap-1.5" role="group" aria-label={`Rate source ${eid}`}>
      {opts.map((o) => (
        <button
          key={o.rating}
          type="button"
          aria-pressed={now === o.rating}
          title={o.label}
          aria-label={o.label}
          onClick={() => desk.rate("chunk", eid, now === o.rating ? "cleared" : o.rating, { section })}
          className={`${btn} ${now === o.rating ? o.on : idle}`}
        >
          {o.icon}
          {o.short}
        </button>
      ))}
    </div>
  );
}

const FLAG_TEXT: Record<string, string> = {
  figure: "a number is not in the cited source",
  subject: "a model name or size is not in the cited source",
  wording: "the sentence's words are barely in the cited source",
  inference: "no citation",
};

/** The chapter's sentences, each with a 🚩 "this is wrong" button and an optional reason. */
export function SentenceFlags({ desk, section }: { desk: Desk; section: string }) {
  const rows = desk.view?.sentences[section] ?? [];
  const [reasons, setReasons] = useState<Record<string, string>>({});
  if (!rows.length) return null;
  const flagged = rows.filter((s) => desk.current("sentence", s.key)).length;
  return (
    <details className="no-print mt-4 border border-border bg-surface px-4 py-3 font-sans text-sm">
      <summary className="cursor-pointer font-semibold">
        Flag a wrong sentence{flagged ? ` · ${flagged} flagged` : ""}
      </summary>
      <ol className="mt-3 space-y-3">
        {rows.map((s) => {
          const on = desk.current("sentence", s.key);
          return (
            <li key={s.key} className={`border-l-[3px] pl-3 ${on ? "border-danger" : "border-border"}`}>
              <div className="leading-relaxed">{s.text}</div>
              {s.flag && <div className="mt-1 text-[11px] font-semibold uppercase tracking-wider text-warning">Check: {FLAG_TEXT[s.flag] ?? s.flag}</div>}
              <div className="mt-1.5 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  aria-pressed={Boolean(on)}
                  onClick={() => desk.rate("sentence", s.key, on ? "cleared" : "wrong", { section, reason: reasons[s.key] ?? "" })}
                  className={`${btn} ${on ? "border-danger bg-danger-soft text-danger" : idle}`}
                >
                  <Flag className="h-3 w-3" />
                  {on ? "Flagged as wrong" : "This is wrong"}
                </button>
                {on && (
                  <input
                    type="text"
                    placeholder="Why? (optional, saved when you leave the box)"
                    defaultValue={on.reason}
                    maxLength={300}
                    onChange={(e) => setReasons((r) => ({ ...r, [s.key]: e.target.value }))}
                    onBlur={(e) => e.target.value !== on.reason && desk.rate("sentence", s.key, "wrong", { section, reason: e.target.value })}
                    className="min-w-0 flex-1 rounded border border-border bg-background px-2 py-1 text-xs"
                  />
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </details>
  );
}
