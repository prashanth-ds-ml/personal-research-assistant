"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

type Item = { kind: string; label: string; hint: string; href: string };

const SCREENS: Item[] = [
  { kind: "Screen", label: "Front page", hint: "home", href: "/" },
  { kind: "Screen", label: "New research brief", hint: "start a goal", href: "/deep" },
  { kind: "Screen", label: "Runs", hint: "everything started", href: "/runs" },
  { kind: "Screen", label: "Reports", hint: "the newsstand", href: "/reports" },
  { kind: "Screen", label: "Library", hint: "your documents", href: "/library" },
  { kind: "Screen", label: "Knowledge graph", hint: "reports and sources", href: "/knowledge" },
  { kind: "Screen", label: "Compare issues", hint: "what changed", href: "/compare" },
  { kind: "Screen", label: "Pipeline graph", hint: "how a run flows", href: "/graph" },
  { kind: "Screen", label: "Quick research", hint: "a short note", href: "/new" },
  { kind: "Screen", label: "Profile", hint: "what it has learned", href: "/profile" },
  { kind: "Screen", label: "Settings", hint: "models, sources, quality", href: "/settings" },
];

/** Ctrl K from anywhere: jump to a screen, a report or a run, or start a brief with the words typed. */
export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [extra, setExtra] = useState<Item[]>([]);
  const [cursor, setCursor] = useState(0);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        onOpenChange(true);
      } else if (e.key === "Escape") {
        onOpenChange(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onOpenChange]);

  useEffect(() => {
    if (!open) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reset the box each time it opens
    setQ("");
    setCursor(0);
    input.current?.focus();
    let alive = true;
    (async () => {
      try {
        const [r, u] = await Promise.all([
          fetch("/api/reports", { cache: "no-store" }).then((x) => x.json()),
          fetch("/api/runs", { cache: "no-store" }).then((x) => x.json()),
        ]);
        if (!alive) return;
        const reports: Item[] = (r.reports ?? []).map((n: { slug: string; title: string; date: string }) => ({
          kind: "Issue",
          label: n.title,
          hint: n.date,
          href: `/research/${n.slug}`,
        }));
        const runs: Item[] = (u.runs ?? []).map((n: { id: string; goal: string; status: string }) => ({
          kind: "Run",
          label: (n.goal || "(no goal)").split("\n")[0].slice(0, 90),
          hint: n.status,
          href: `/runs/${n.id}`,
        }));
        setExtra([...reports, ...runs]);
      } catch {
        setExtra([]);
      }
    })();
    return () => {
      alive = false;
    };
  }, [open]);

  const results = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const all = [...SCREENS, ...extra];
    return all.filter((i) => !needle || `${i.label} ${i.kind} ${i.hint}`.toLowerCase().includes(needle)).slice(0, 9);
  }, [q, extra]);

  const go = (item: Item | undefined) => {
    onOpenChange(false);
    if (item) router.push(item.href);
    else if (q.trim()) router.push(`/deep?goal=${encodeURIComponent(q.trim())}`);
  };

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-ink/50 px-4 pt-28" onClick={() => onOpenChange(false)}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Search everything"
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl overflow-hidden rounded border border-border bg-surface shadow-2xl"
      >
        <input
          ref={input}
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setCursor(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setCursor((c) => Math.min(c + 1, results.length - 1));
            } else if (e.key === "ArrowUp") {
              e.preventDefault();
              setCursor((c) => Math.max(c - 1, 0));
            } else if (e.key === "Enter") {
              e.preventDefault();
              go(results[cursor]);
            }
          }}
          aria-label="Search everything"
          placeholder="Search reports, runs, screens"
          className="w-full border-b-2 border-foreground bg-transparent px-6 py-5 font-serif text-xl outline-none"
        />
        <ul className="max-h-96 overflow-auto py-1">
          {results.map((r, i) => (
            <li key={`${r.kind}-${r.href}-${i}`}>
              <button
                type="button"
                onClick={() => go(r)}
                onMouseEnter={() => setCursor(i)}
                className={`flex w-full items-baseline gap-4 px-6 py-2.5 text-left text-sm ${i === cursor ? "bg-surface-hover" : ""}`}
              >
                <span className="w-14 shrink-0 text-[11px] font-semibold uppercase tracking-widest text-accent">{r.kind}</span>
                <span className="flex-1 font-medium">{r.label}</span>
                <span className="text-xs text-muted">{r.hint}</span>
              </button>
            </li>
          ))}
          {results.length === 0 && (
            <li className="px-6 py-6 font-serif text-lg italic text-muted">
              Nothing matches. Press Enter to start a new brief with these words.
            </li>
          )}
        </ul>
        <div className="border-t border-border px-6 py-2 text-xs text-muted">
          Arrow keys to move, Enter to open, Esc to close. Ctrl K works from anywhere.
        </div>
      </div>
    </div>
  );
}
