"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { SessionEntry } from "@/lib/profile";
import { useToast } from "@/components/toast";
import { useUnsavedGuard } from "@/lib/use-unsaved-guard";

export interface Lesson {
  slug: string;
  text: string;
  from: string;
}

const card = "border border-border border-t-[3px] border-t-foreground bg-surface p-5";
const btn = "rounded px-4 py-2.5 text-sm font-semibold disabled:opacity-40";
const primary = `${btn} bg-accent text-accent-foreground hover:opacity-90`;
const ghost = `${btn} border border-foreground hover:bg-foreground hover:text-background`;
const danger = `${btn} border border-danger text-danger hover:bg-danger hover:text-accent-foreground`;

export function ProfileView({ raw, standing, entries, topics, lessons }: { raw: string; standing: string; entries: SessionEntry[]; topics: string[]; lessons: Lesson[] }) {
  const router = useRouter();
  const toast = useToast();
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState(raw);
  const [confirm, setConfirm] = useState(false);
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  useUnsavedGuard(editing && text !== raw);

  const post = async (body: unknown) => {
    setBusy(true);
    try {
      const res = await fetch("/api/profile", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
      const b = (await res.json()) as { ok?: boolean; error?: string };
      return { ok: Boolean(b.ok), error: b.error ?? "That did not work." };
    } catch {
      return { ok: false, error: "Could not reach the dashboard server." };
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    const r = await post({ action: "save", text });
    setNote(r.ok ? null : { ok: false, text: r.error });
    toast(r.ok ? "success" : "error", r.ok ? "Saved. The previous version was kept as Profile.md.bak-<date> in your vault." : r.error);
    if (r.ok) {
      setEditing(false);
      router.refresh();
    }
  };
  const reset = async () => {
    setConfirm(false);
    const r = await post({ action: "reset" });
    setNote(r.ok ? null : { ok: false, text: r.error });
    toast(r.ok ? "success" : "error", r.ok ? "The profile is a blank template again. The old note was kept as a backup in your vault." : r.error);
    if (r.ok) {
      setText("");
      router.refresh();
    }
  };
  const forget = async (slug: string) => {
    await fetch("/api/feedback", { method: "DELETE", headers: { "content-type": "application/json" }, body: JSON.stringify({ slug }) });
    toast("success", "Forgotten. The planner will not use that note any more.");
    router.refresh();
  };

  return (
    <div className="mx-auto max-w-5xl">
      <div className="flex flex-wrap items-end gap-4">
        <div>
          <div className="kicker">About the reader</div>
          <h1 className="mt-1 text-5xl leading-none">Profile</h1>
        </div>
        <div className="flex-1" />
        <button type="button" onClick={() => { setEditing((v) => !v); setText(raw); }} className={ghost}>
          {editing ? "Cancel editing" : "Edit the note"}
        </button>
      </div>
      <p className="mb-6 mt-3 text-sm text-muted">What the assistant has learned about you. It is a plain note in your vault (Profile.md): the assistant only appends to the Session Log, and the Standing Preferences are yours to edit.</p>

      {editing && (
        <div className={`${card} mb-5`}>
          <label htmlFor="pn" className="text-[13px] text-muted">
            Profile.md
          </label>
          <textarea id="pn" value={text} onChange={(e) => setText(e.target.value)} className="mt-2 h-80 w-full rounded border border-border bg-background p-3 font-mono text-[13px] leading-relaxed outline-none focus:border-accent" />
          <div className="mt-3 flex gap-3">
            <button type="button" onClick={save} disabled={busy} className={primary}>
              Save to the vault
            </button>
            <button type="button" onClick={() => setEditing(false)} className={ghost}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className={`${card} mb-5`}>
        <div className="font-serif text-2xl">Standing preferences</div>
        {standing ? <p className="mt-2 whitespace-pre-line text-[15px] leading-relaxed">{standing}</p> : <p className="mt-2 text-sm text-muted">Nothing written yet. Use “Edit the note” to say what every run should account for: depth, tone, topics to avoid.</p>}
      </div>

      <div className="grid gap-5 md:grid-cols-2">
        <div className={card}>
          <div className="mb-3 font-serif text-2xl">Topics it has learned from</div>
          {topics.length === 0 ? (
            <p className="text-sm text-muted">
              None yet. Quick research adds a topic here after each note.{" "}
              <a href="/new" className="font-semibold text-accent hover:underline">
                Run a quick research →
              </a>
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {topics.slice(0, 24).map((t) => (
                <span key={t} className="rounded border border-accent bg-accent-soft px-3 py-1.5 text-[13px]">
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className={card}>
          <div className="mb-3 font-serif text-2xl">What your feedback taught it</div>
          {lessons.length === 0 && <p className="text-sm text-muted">
              Nothing yet. Rate a report to teach it.{" "}
              <a href="/reports" className="font-semibold text-accent hover:underline">
                Open your reports →
              </a>
            </p>}
          {lessons.map((l) => (
            <div key={l.slug} className="flex gap-3 border-t border-border py-2.5 text-sm leading-snug">
              <span className="flex-1">
                {l.text}
                <br />
                <span className="text-xs text-muted">{l.from}</span>
              </span>
              <button type="button" onClick={() => forget(l.slug)} className="text-xs font-semibold text-accent hover:underline">
                Forget
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className={`${card} mt-5`}>
        <div className="mb-2 font-serif text-2xl">Recent additions</div>
        {entries.length === 0 && (
          <p className="text-sm text-muted">
            Nothing yet. Each finished quick research adds an entry here.{" "}
            <a href="/new" className="font-semibold text-accent hover:underline">
              Start one →
            </a>
          </p>
        )}
        {entries.slice(0, 8).map((e, i) => (
          <div key={`${e.date}-${i}`} className="flex gap-4 border-t border-border py-2.5 text-sm leading-snug">
            <span className="w-24 shrink-0 text-muted">{e.date}</span>
            <span>
              <b>{e.title || "(untitled)"}</b>
              {e.bullets[0] && <span className="block text-muted">{e.bullets[0].slice(0, 200)}</span>}
            </span>
          </div>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-3">
        <button type="button" onClick={() => setConfirm(true)} disabled={busy} className={danger}>
          Reset what it has learned
        </button>
        {note && !note.ok && <span className="text-sm text-danger">{note.text}</span>}
      </div>
      {confirm && (
        <div className="mt-4 border border-danger p-4 text-sm leading-relaxed">
          <b>Reset the profile?</b> The note goes back to a blank template (a backup copy is kept in your vault). Reports and sources are not touched.
          <div className="mt-3 flex gap-2">
            <button type="button" onClick={reset} className={danger}>
              Yes, reset
            </button>
            <button type="button" onClick={() => setConfirm(false)} className={ghost}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
