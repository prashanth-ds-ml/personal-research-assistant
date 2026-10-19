"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { kindLabel, type DocKind, type LibraryDoc } from "@/lib/library-types";
import { useToast } from "@/components/toast";
import { useUnsavedGuard } from "@/lib/use-unsaved-guard";

const TABS: { key: "all" | DocKind; label: string }[] = [
  { key: "all", label: "All" },
  { key: "pdf", label: "PDFs and papers" },
  { key: "web", label: "Web pages" },
  { key: "hf", label: "Hugging Face" },
  { key: "doc", label: "Local documents" },
];

const KIND_STYLE: Record<DocKind, string> = {
  pdf: "bg-info/15 text-info",
  web: "bg-success-soft text-success",
  hf: "bg-warning-soft text-warning",
  doc: "bg-surface-hover text-muted",
};

const btn = "rounded px-4 py-2.5 text-sm font-semibold";
const primary = `${btn} bg-accent text-accent-foreground hover:opacity-90 disabled:opacity-40`;
const ghost = `${btn} border border-foreground hover:bg-foreground hover:text-background disabled:opacity-40`;
const danger = `${btn} border border-danger text-danger hover:bg-danger hover:text-accent-foreground disabled:opacity-40`;

export function LibraryView({ docs }: { docs: LibraryDoc[] }) {
  const router = useRouter();
  const toast = useToast();
  const [tab, setTab] = useState<"all" | DocKind>("all");
  const [q, setQ] = useState("");
  const [selId, setSelId] = useState<string | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [adding, setAdding] = useState(false);
  const [urls, setUrls] = useState("");
  const [job, setJob] = useState<{ id: string; status: string; summary: string; lines: string[] } | null>(null);
  const [addMsg, setAddMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const poll = useRef<ReturnType<typeof setTimeout> | null>(null);

  useUnsavedGuard(adding && urls.trim().length > 0, "The addresses you pasted have not been fetched yet. Leave anyway?");
  const sel = docs.find((d) => d.id === selId) ?? null;
  const shown = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return docs.filter((d) => (tab === "all" || d.kind === tab) && (!needle || `${d.title} ${d.site}`.toLowerCase().includes(needle)));
  }, [docs, tab, q]);
  const count = (k: "all" | DocKind) => (k === "all" ? docs.length : docs.filter((d) => d.kind === k).length);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- the preview is fetched when the selection changes
    setPreview(null);
    if (!selId) return;
    let alive = true;
    fetch(`/api/library/preview?id=${encodeURIComponent(selId)}`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : { text: null }))
      .then((b: { text: string | null }) => alive && setPreview(b.text))
      .catch(() => alive && setPreview(null));
    return () => {
      alive = false;
    };
  }, [selId]);

  useEffect(
    () => () => {
      if (poll.current) clearTimeout(poll.current);
    },
    []
  );

  const act = async (action: "reindex" | "remove") => {
    if (!sel) return;
    setBusy(true);
    setConfirm(false);
    setNote({ ok: true, text: action === "reindex" ? "Re-indexing: converting and embedding again. A PDF can take a minute." : "Removing..." });
    try {
      const res = await fetch("/api/library/doc", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ action, id: sel.id }) });
      const body = (await res.json()) as { ok?: boolean; error?: string; outcome?: string; moved_to?: string };
      if (!body.ok) {
        setNote({ ok: false, text: body.error ?? "That did not work." });
        toast("error", body.error ?? "That did not work.");
      } else if (action === "remove") {
        setNote(null);
        setSelId(null);
        toast("success", "Removed from the library. The file is in the vault's .removed folder if you want it back.");
        router.refresh();
      } else {
        setNote(null);
        toast("success", body.outcome === "unchanged" ? "Re-indexed. Nothing had changed." : "Re-indexed.");
        router.refresh();
      }
    } catch {
      setNote({ ok: false, text: "Could not reach the dashboard server." });
    } finally {
      setBusy(false);
    }
  };

  const watch = (id: string) => {
    const tick = async () => {
      try {
        const r = await fetch(`/api/library/jobs/${id}`, { cache: "no-store" });
        const b = (await r.json()) as { status: string; summary: string; lines: string[] };
        setJob({ id, ...b });
        if (b.status === "running") {
          poll.current = setTimeout(tick, 2000);
        } else {
          setAddMsg({ ok: b.status === "done", text: b.status === "done" ? `Added. ${b.summary || "The new pages are indexed below."}` : `It did not finish: ${b.summary}` });
          toast(b.status === "done" ? "success" : "error", b.status === "done" ? "Sources added and indexed." : `Adding sources did not finish: ${b.summary}`);
          setBusy(false);
          router.refresh();
        }
      } catch {
        poll.current = setTimeout(tick, 4000);
      }
    };
    tick();
  };

  const submitAdd = async () => {
    const list = urls.split(/\s+/).filter(Boolean);
    if (list.length === 0) return;
    setBusy(true);
    setAddMsg(null);
    try {
      const res = await fetch("/api/library/add", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ urls: list }) });
      const body = (await res.json()) as { job?: string; accepted?: number; skipped?: number; error?: string };
      if (!res.ok || !body.job) {
        setAddMsg({ ok: false, text: body.error ?? "Could not start." });
        setBusy(false);
        return;
      }
      setAddMsg({ ok: true, text: `Fetching ${body.accepted} address${body.accepted === 1 ? "" : "es"}${body.skipped ? ` (${body.skipped} skipped: not a web address)` : ""}...` });
      setUrls("");
      watch(body.job);
    } catch {
      setAddMsg({ ok: false, text: "Could not reach the dashboard server." });
      setBusy(false);
    }
  };

  return (
    <div className="grid min-h-[calc(100vh-9rem)] gap-8 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div className="min-w-0">
        <div className="mb-6 flex flex-wrap items-end gap-4">
          <div>
            <div className="kicker">The archive</div>
            <h1 className="mt-1 text-5xl leading-none">Library</h1>
            <p className="mt-3 text-sm text-muted">{docs.length} documents indexed. Deep research reads these.</p>
          </div>
          <div className="flex-1" />
          <button type="button" onClick={() => setAdding((v) => !v)} className={primary}>
            + Add sources
          </button>
        </div>

        {adding && (
          <div className="mb-6 border border-border border-t-4 border-t-accent bg-surface p-5">
            <label htmlFor="urls" className="text-[11px] font-semibold uppercase tracking-widest text-muted">
              Pages or PDFs to add (one address per line)
            </label>
            <textarea
              id="urls"
              value={urls}
              onChange={(e) => setUrls(e.target.value)}
              placeholder="https://example.org/a-useful-article"
              className="mt-2 h-24 w-full resize-none rounded border border-border bg-background p-3 text-sm outline-none focus:border-accent"
            />
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <button type="button" onClick={submitAdd} disabled={busy || !urls.trim()} className={primary}>
                Fetch and index
              </button>
              <button type="button" onClick={() => setAdding(false)} className={ghost}>
                Cancel
              </button>
              <span className="text-sm text-muted">robots.txt is respected; paywalled or login pages are skipped.</span>
            </div>
            {addMsg && <div className={`mt-3 border px-4 py-3 text-sm ${addMsg.ok ? "border-success text-success" : "border-danger text-danger"}`}>{addMsg.text}</div>}
            {job && job.status === "running" && job.lines.length > 0 && (
              <pre className="mt-3 max-h-40 overflow-auto rounded border border-border bg-background p-3 text-xs leading-relaxed text-muted">{job.lines.join("\n")}</pre>
            )}
          </div>
        )}

        <div className="mb-4 flex flex-wrap items-center gap-2">
          {TABS.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setTab(t.key)}
              aria-pressed={tab === t.key}
              className={`rounded px-3.5 py-2 text-[13.5px] font-semibold ${tab === t.key ? "bg-accent-soft text-accent ring-1 ring-accent" : "border border-border hover:border-accent"}`}
            >
              {t.label} <span className="opacity-60">{count(t.key)}</span>
            </button>
          ))}
          <div className="flex-1" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            aria-label="Search the library"
            placeholder="Search titles"
            className="w-60 rounded border border-border bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
          />
        </div>

        <div className="border border-border border-t-[3px] border-t-foreground bg-surface">
          <div className="grid grid-cols-[minmax(0,1fr)_96px] gap-3 px-4 py-3 text-[11px] md:grid-cols-[minmax(0,1fr)_120px_170px_70px] font-semibold uppercase tracking-widest text-muted">
            <span>Title</span>
            <span>Type</span>
            <span className="hidden md:block">Source</span>
            <span className="hidden md:block">Facts</span>
          </div>
          {shown.map((d) => (
            <button
              key={d.id}
              type="button"
              onClick={() => {
                setSelId(d.id);
                setConfirm(false);
                setNote(null);
                // on a phone the details panel sits below the table: bring it into view
                if (window.matchMedia("(max-width: 1023px)").matches) setTimeout(() => document.getElementById("doc-details")?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
              }}
              className={`grid w-full grid-cols-[minmax(0,1fr)_96px] items-center gap-3 border-t md:grid-cols-[minmax(0,1fr)_120px_170px_70px] border-border px-4 py-3.5 text-left hover:bg-surface-hover ${selId === d.id ? "bg-accent-soft" : ""}`}
            >
              <span className="line-clamp-2 font-serif text-lg leading-snug md:truncate">
                {d.title}
                {d.status !== "ok" && <span className="ml-2 rounded bg-danger-soft px-1.5 py-0.5 font-sans text-[10px] font-semibold uppercase text-danger">{d.status === "failed" ? "unreadable" : "empty"}</span>}
              </span>
              <span>
                <span className={`rounded px-2 py-0.5 text-xs font-semibold ${KIND_STYLE[d.kind]}`}>{kindLabel(d.kind)}</span>
              </span>
              <span className="hidden truncate text-[13px] text-muted md:block">{d.site}</span>
              <span className="hidden text-sm md:block" title={d.facts ? `${d.facts} facts used in reports` : "No report has used this document yet"}>
                {d.facts || "—"}
              </span>
            </button>
          ))}
          {shown.length === 0 && (
            <div className="px-6 py-16 text-center">
              <div className="font-serif text-4xl leading-tight">{docs.length === 0 ? "The shelves are empty." : "Nothing filed under that."}</div>
              <p className="mt-2 font-serif text-xl italic text-muted">
                {docs.length === 0 ? "Add a few sources above, or drop PDFs into the Library folder of your vault." : "Clear the search, pick another type, or add sources."}
              </p>
            </div>
          )}
        </div>
      </div>

      <aside id="doc-details" className="scroll-mt-4 self-start border border-border border-t-4 border-t-accent bg-surface p-6 lg:sticky lg:top-6">
        {!sel ? (
          <div>
            <div className="kicker text-muted">No document selected</div>
            <p className="mt-2 text-[15px] leading-relaxed">Click a row to see what it holds, where it came from and which reports used it.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <span className={`w-fit rounded px-2.5 py-1 text-xs font-semibold ${KIND_STYLE[sel.kind]}`}>{kindLabel(sel.kind)}</span>
            <div className="font-serif text-2xl leading-snug">{sel.title}</div>
            <div className="text-[13px] text-muted">
              {sel.site} · added {sel.added}
            </div>
            <div className="my-1 flex gap-8">
              <div>
                <div className="font-serif text-4xl leading-none">{sel.chunks}</div>
                <div className="text-[13px] text-muted">chunks</div>
              </div>
              <div>
                <div className="font-serif text-4xl leading-none">{sel.facts}</div>
                <div className="text-[13px] text-muted">facts used</div>
              </div>
            </div>
            {sel.error && <div className="border border-danger px-3 py-2 text-xs text-danger">{sel.error}</div>}
            <div className="text-[11px] font-semibold uppercase tracking-widest text-muted">Preview</div>
            <p className="max-h-64 overflow-auto whitespace-pre-line rounded border border-border bg-background p-3 text-sm leading-relaxed">
              {preview ?? (sel.status === "ok" ? "Loading..." : "Nothing readable was found in this file.")}
            </p>
            <div className="mt-2 flex flex-col gap-2">
              {sel.url ? (
                <a href={sel.url} target="_blank" rel="noopener noreferrer nofollow" className={`${primary} text-center`}>
                  Open original
                </a>
              ) : (
                <a href={`/api/library/file?id=${encodeURIComponent(sel.id)}`} target="_blank" rel="noopener noreferrer" className={`${primary} text-center`}>
                  Open the file
                </a>
              )}
              <button type="button" onClick={() => act("reindex")} disabled={busy} className={ghost}>
                Re-index this document
              </button>
              <button type="button" onClick={() => setConfirm(true)} disabled={busy} className={danger}>
                Remove from library
              </button>
            </div>
            {confirm && (
              <div className="border border-danger p-4 text-sm leading-relaxed">
                <b>Remove it?</b> It stops being searched. The file is moved to the vault&apos;s <code>.removed</code> folder, not deleted.
                <div className="mt-3 flex gap-2">
                  <button type="button" onClick={() => act("remove")} className={danger}>
                    Yes, remove
                  </button>
                  <button type="button" onClick={() => setConfirm(false)} className={ghost}>
                    Cancel
                  </button>
                </div>
              </div>
            )}
            {note && <div className={`border px-4 py-3 text-sm ${note.ok ? "border-success text-success" : "border-danger text-danger"}`}>{note.text}</div>}
          </div>
        )}
      </aside>
    </div>
  );
}
