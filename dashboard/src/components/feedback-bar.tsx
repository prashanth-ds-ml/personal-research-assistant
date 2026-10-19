"use client";

import { useState } from "react";
import { ThumbsDown, ThumbsUp, Check } from "lucide-react";

type Rating = "up" | "down";

export function FeedbackBar({
  slug,
  initialRating,
  initialNote,
}: {
  slug: string;
  initialRating?: Rating;
  initialNote?: string;
}) {
  const [rating, setRating] = useState<Rating | undefined>(initialRating);
  const [note, setNote] = useState(initialNote ?? "");
  const [saved, setSaved] = useState(Boolean(initialRating));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const save = async (next: Rating) => {
    setBusy(true);
    setError("");
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slug, rating: next, note }),
      });
      if (!res.ok) throw new Error((await res.json()).error ?? `HTTP ${res.status}`);
      setRating(next);
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save feedback");
    } finally {
      setBusy(false);
    }
  };

  const base =
    "flex items-center gap-1.5 rounded border px-3.5 py-1.5 text-sm font-medium transition-colors disabled:opacity-50";
  const idle = "border-border text-muted hover:border-accent/40 hover:text-accent";
  const on = "border-accent bg-accent-soft text-accent";

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-border bg-surface p-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm font-medium">Was this report useful?</span>
        <button type="button" disabled={busy} onClick={() => save("up")} className={`${base} ${rating === "up" ? on : idle}`}>
          <ThumbsUp className="h-4 w-4" /> Useful
        </button>
        <button type="button" disabled={busy} onClick={() => save("down")} className={`${base} ${rating === "down" ? on : idle}`}>
          <ThumbsDown className="h-4 w-4" /> Not useful
        </button>
        {saved && !busy && (
          <span className="flex items-center gap-1 text-xs text-success">
            <Check className="h-3.5 w-3.5" /> Saved
          </span>
        )}
      </div>
      <label className="flex flex-col gap-1.5">
        <span className="text-xs text-muted">
          What worked or what was missing? Short notes help the next plan (for example: &quot;too generic, wanted numbers&quot;).
        </span>
        <input
          className="w-full rounded-xl border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent focus:ring-2 focus:ring-accent/20"
          value={note}
          onChange={(e) => {
            setNote(e.target.value);
            setSaved(false);
          }}
          onBlur={() => rating && !saved && save(rating)}
          placeholder="Optional note"
          maxLength={1000}
        />
      </label>
      {error && <p className="text-xs text-warning">{error}</p>}
    </div>
  );
}
