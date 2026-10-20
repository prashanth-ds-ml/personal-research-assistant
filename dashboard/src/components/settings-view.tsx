"use client";

import { useEffect, useRef, useState } from "react";
import { useToast } from "@/components/toast";
import { useUnsavedGuard } from "@/lib/use-unsaved-guard";

type Values = Record<string, string>;
type Tab = "models" | "sources" | "quality" | "library" | "privacy";

const TABS: { key: Tab; label: string; heading: string; sub: string }[] = [
  { key: "models", label: "Models", heading: "Models", sub: "Which local model does each job. All run through Ollama on this machine." },
  { key: "sources", label: "Sources", heading: "Sources", sub: "Where the collector looks, and what it may bring in." },
  { key: "quality", label: "Report quality", heading: "Report quality", sub: "How strict the evidence gate is, and what gets labelled." },
  { key: "library", label: "Library and vault", heading: "Library and vault", sub: "Where your documents live and what gets indexed." },
  { key: "privacy", label: "Privacy", heading: "Privacy", sub: "What leaves this machine, and what never does." },
];

const card = "border border-border border-t-[3px] border-t-foreground bg-surface";
const btn = "rounded px-4 py-2.5 text-sm font-semibold disabled:opacity-40";
const primary = `${btn} bg-accent text-accent-foreground hover:opacity-90`;
const ghost = `${btn} border border-foreground hover:bg-foreground hover:text-background`;
const hint = "mt-3 text-[13px] leading-relaxed text-muted";

const isTrue = (v: string) => v === "True";

export function SettingsView({ values: initial, defaults, installed, vault, library }: { values: Values; defaults: Values; installed: string[]; vault: string; library: { folder: string; docs: number }[] }) {
  const toast = useToast();
  const [tab, setTab] = useState<Tab>("models");
  const [v, setV] = useState<Values>(initial);
  const [saved, setSaved] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [job, setJob] = useState<{ status: string; summary: string; lines: string[] } | null>(null);
  const poll = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(
    () => () => {
      if (poll.current) clearTimeout(poll.current);
    },
    []
  );

  const dirty = Object.keys(v).some((k) => v[k] !== initial[k]);
  useUnsavedGuard(dirty);
  const set = (k: string, val: string) => {
    setV((o) => ({ ...o, [k]: val }));
    setSaved(null);
  };
  const flip = (k: string) => set(k, isTrue(v[k]) ? "False" : "True");

  const save = async (body: unknown, done: string) => {
    setBusy(true);
    try {
      const res = await fetch("/api/settings", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) });
      const b = (await res.json()) as { ok?: boolean; error?: string };
      setSaved(b.ok ? { ok: true, text: done } : { ok: false, text: b.error ?? "That did not work." });
      toast(b.ok ? "success" : "error", b.ok ? done : (b.error ?? "That did not work."));
      return Boolean(b.ok);
    } catch {
      setSaved({ ok: false, text: "Could not reach the dashboard server." });
      return false;
    } finally {
      setBusy(false);
    }
  };

  const onSave = async () => {
    const changes = Object.fromEntries(Object.keys(v).filter((k) => v[k] !== initial[k]).map((k) => [k, v[k]]));
    const ok = await save({ changes }, "Saved to the .env file. The research backend reads it when it starts: restart it (langgraph dev) to apply.");
    if (ok) Object.assign(initial, v);
  };
  const onReset = async () => {
    if (await save({ reset: true }, "Back to the defaults. Restart the research backend to apply.")) {
      setV({ ...defaults });
      Object.assign(initial, defaults);
    }
  };

  const runJob = async (mode: "refresh" | "rebuild") => {
    setJob({ status: "running", summary: "", lines: [] });
    try {
      const res = await fetch("/api/library/reindex", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ mode }) });
      const b = (await res.json()) as { job?: string; error?: string };
      if (!b.job) {
        setJob({ status: "failed", summary: b.error ?? "Could not start.", lines: [] });
        return;
      }
      const tick = async () => {
        const r = await fetch(`/api/library/jobs/${b.job}`, { cache: "no-store" });
        const s = (await r.json()) as { status: string; summary: string; lines: string[] };
        setJob(s);
        if (s.status === "running") poll.current = setTimeout(tick, 2500);
        else toast(s.status === "done" ? "success" : "error", s.status === "done" ? "Library updated." : `It did not finish: ${s.summary}`);
      };
      void tick();
    } catch {
      setJob({ status: "failed", summary: "Could not reach the dashboard server.", lines: [] });
    }
  };

  const toggle = (k: string, label: string, help: string, where: string) => (
    <label key={k} className={`${card} mb-2.5 flex cursor-pointer items-center gap-3.5 px-[18px] py-3.5`}>
      <input type="checkbox" checked={isTrue(v[k])} onChange={() => flip(k)} className="h-4 w-4 accent-accent" />
      <span className="flex-1">
        <b className="text-[15px]">{label}</b>
        <br />
        <span className="text-[13px] text-muted">{help}</span>
      </span>
      <span className="rounded border border-border px-2 py-0.5 text-[11px] font-semibold text-muted">{where}</span>
    </label>
  );

  const llms = installed.filter((m) => !/embed/i.test(m));
  const embeds = installed.filter((m) => /embed/i.test(m)).map((m) => `ollama:${m}`);
  const withCurrent = (list: string[], cur: string) => (list.includes(cur) ? list : [cur, ...list]);
  const model = (key: string, role: string, why: string, options: string[]) => (
    <div key={key} className={`${card} mb-3 flex items-center gap-4 px-[18px] py-4`}>
      <div className="flex-1">
        <div className="text-[15px] font-semibold">{role}</div>
        <div className="text-[13px] text-muted">{why}</div>
      </div>
      <label htmlFor={key} className="sr-only">
        {role}
      </label>
      <select id={key} value={v[key]} onChange={(e) => set(key, e.target.value)} className="rounded border border-border bg-background px-3 py-2.5 font-mono text-sm outline-none focus:border-accent">
        {withCurrent(options, v[key]).map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );

  const sites = withCurrent([...(v.COLLECT_EXTRA_SITES ? v.COLLECT_EXTRA_SITES.split(";") : [])], "").filter(Boolean);
  const allSites = Array.from(new Set([...defaults.COLLECT_EXTRA_SITES.split(";"), ...sites]));
  const siteOn = (s: string) => sites.includes(s);
  const toggleSite = (s: string) => set("COLLECT_EXTRA_SITES", allSites.filter((x) => (x === s ? !siteOn(s) : siteOn(x))).join(";"));

  const step = (k: string, min: number, max: number) => (
    <span className="inline-flex items-center gap-2">
      <button type="button" aria-label="Fewer" onClick={() => set(k, String(Math.max(min, Number(v[k]) - 1)))} className="h-8 w-8 rounded-full border border-border hover:border-accent">
        −
      </button>
      <b className="min-w-5 text-center text-xl">{v[k]}</b>
      <button type="button" aria-label="More" onClick={() => set(k, String(Math.min(max, Number(v[k]) + 1)))} className="h-8 w-8 rounded-full border border-border hover:border-accent">
        +
      </button>
    </span>
  );

  const cur = TABS.find((t) => t.key === tab)!;
  return (
    <div className="grid min-h-[calc(100vh-9rem)] gap-0 lg:grid-cols-[230px_minmax(0,1fr)]">
      <div className="border-border pb-6 pr-0 lg:border-r lg:pr-5">
        <div className="kicker">The editor&apos;s notes</div>
        <h1 className="mb-4 mt-1 text-5xl leading-none">Settings</h1>
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            aria-current={tab === t.key ? "page" : undefined}
            onClick={() => {
              setTab(t.key);
              setSaved(null);
            }}
            className={`mb-1 block w-full rounded px-3 py-2.5 text-left text-[15px] ${tab === t.key ? "bg-accent-soft font-semibold text-accent" : "hover:bg-surface-hover"}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="min-w-0 lg:pl-9">
        <div className="max-w-3xl">
          <h2 className="text-4xl">{cur.heading}</h2>
          <p className="mb-5 mt-1 text-sm text-muted">{cur.sub}</p>

          {tab === "models" && (
            <>
              {model("LOCAL_LLM", "Model", "One model plans, judges which passages are useful and writes the report.", llms)}
              {model("WRITER_MODEL", "Writer (optional)", "Leave blank to use the same model; set only to compare another writer.", llms)}
              {model("EMBEDDING_MODEL", "Embeddings", "Turns text into vectors for search. Changing it needs a library rebuild.", embeds)}
              <p className={hint}>Only one model sits in GPU memory at a time. The writer needs about 5.4 GB of free system RAM. The lists show the models Ollama has installed.</p>
            </>
          )}

          {tab === "sources" && (
            <>
              {toggle("COLLECT_HUGGINGFACE", "Search Hugging Face", "Papers, model cards and dataset cards for each question.", "setting")}
              {toggle("COLLECT_AI_SITES", "Search AI-engineering sites", "Site-restricted searches over the list below.", "setting")}
              {toggle("COLLECT_EUROPEPMC", "Search Europe PMC", "Open-access biomedical papers. Turn off for AI and software topics.", "setting")}
              <label className={`${card} mb-2.5 flex cursor-pointer items-center gap-3.5 px-[18px] py-3.5`}>
                <input type="checkbox" checked={v.FETCH_MAX_SOURCES === "0"} onChange={() => set("FETCH_MAX_SOURCES", v.FETCH_MAX_SOURCES === "0" ? "30" : "0")} className="h-4 w-4 accent-accent" />
                <span className="flex-1">
                  <b className="text-[15px]">No limit on collected sources</b>
                  <br />
                  <span className="text-[13px] text-muted">You choose what to keep in the review step.{v.FETCH_MAX_SOURCES !== "0" ? ` Now capped at ${v.FETCH_MAX_SOURCES}.` : ""}</span>
                </span>
                <span className="rounded border border-border px-2 py-0.5 text-[11px] font-semibold text-muted">setting</span>
              </label>
              <div className="mb-2.5 mt-5 text-[13px] font-semibold uppercase tracking-[0.08em] text-muted">AI-engineering sites searched for every question</div>
              <div className="flex flex-wrap gap-2">
                {allSites.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => toggleSite(s)}
                    aria-pressed={siteOn(s)}
                    className={`rounded border px-3 py-1.5 text-[13px] ${siteOn(s) ? "border-accent bg-accent-soft" : "border-border text-muted line-through"}`}
                  >
                    {s}
                  </button>
                ))}
              </div>
              <p className={hint}>Grouped in sixes: the first group is the Raschka, Karpathy and Alammar blogs, so bigger sites cannot drown them.</p>
            </>
          )}

          {tab === "quality" && (
            <>
              {toggle("COVERAGE_CHECK", "Coverage check at plan approval", "Marks each question covered, thin or nothing before any long work.", "setting")}
              {toggle("CLAIM_LABELS", "Check every sentence", "Flags a number, model name or wording not found in the cited source, and uncited sentences.", "setting")}
              {toggle("PLAN_THINKING", "Think when planning", "About 85 s per plan instead of 8 s; plans vary between runs.", "setting")}
              {toggle("WRITE_THINKING", "Think when writing", "About 90 s per section instead of 9 s; in tests it cited more passages and left nothing uncited.", "setting")}
              {toggle("REQUIRE_PLAN_APPROVAL", "Ask me to approve the plan", "Off lets a run go unattended.", "setting")}
              {toggle("ASK_CLARIFYING_QUESTIONS", "Ask clarifying questions", "Off skips straight to the plan.", "setting")}
              <div className={`${card} px-[18px] py-4`}>
                <div className="mb-2 text-[15px] font-semibold">A section is written from evidence only if it has</div>
                <div className="flex flex-wrap items-center gap-8 text-sm">
                  <span className="flex items-center gap-2">
                    {step("MIN_SECTION_FACTS", 1, 20)} passages
                  </span>
                  <span className="flex items-center gap-2">
                    {step("MIN_SECTION_DOCUMENTS", 1, 10)} documents
                  </span>
                </div>
                <p className="mt-2 text-[13px] text-muted">Below this it says what is missing instead of writing filler. If under half the sections qualify, the report is a gap report with no recommendation.</p>
              </div>
            </>
          )}

          {tab === "library" && (
            <>
              <div className={`${card} mb-3 px-[18px] py-4`}>
                <div className="text-[13px] text-muted">Vault</div>
                <div className="mt-1 font-mono text-sm">{vault || "(VAULT_PATH is not set)"}</div>
              </div>
              <div className={`${card} mb-3 px-[18px] py-4`}>
                <div className="text-[13px] text-muted">Library folders (indexed at the start of every run)</div>
                <div className="mt-1.5 font-mono text-sm leading-[1.8]">
                  {library.map((f) => (
                    <div key={f.folder}>
                      {f.folder}/ <span className="font-sans text-[13px] text-muted">{f.docs} documents</span>
                    </div>
                  ))}
                </div>
              </div>
              {toggle("INCLUDE_ARCHIVED_PAGES", "Include archived copies of your own documents", "Off by default: they only repeat files already in the library.", "setting")}
              <div className="mt-3 flex flex-wrap gap-3">
                <button type="button" onClick={() => runJob("refresh")} disabled={job?.status === "running"} className={ghost}>
                  Re-index the library
                </button>
                <button type="button" onClick={() => runJob("rebuild")} disabled={job?.status === "running"} className={ghost}>
                  Rebuild after changing the embedding model
                </button>
              </div>
              {job && (
                <div className={`mt-3 border px-4 py-3 text-sm ${job.status === "failed" ? "border-danger text-danger" : job.status === "done" ? "border-success text-success" : "border-border text-muted"}`}>
                  {job.status === "running" ? "Working... only new or changed files are converted." : job.summary}
                  {job.status === "running" && job.lines.length > 0 && <pre className="mt-2 max-h-32 overflow-auto text-xs">{job.lines.slice(-6).join("\n")}</pre>}
                </div>
              )}
            </>
          )}

          {tab === "privacy" && (
            <>
              <div className={`${card} mb-3 p-5 text-[15px] leading-[1.7]`}>
                <b>What stays on this machine:</b> your documents, the library, every model call, reports and the profile.
                <br />
                <b>What goes out:</b> web and paper searches, and downloads of the sources you choose. Nothing else.
              </div>
              {toggle("LANGCHAIN_TRACING_V2", "Send run traces to LangSmith", "Off: traces stay local. On uploads your prompts and research to a cloud service (it also needs an API key in .env).", "setting")}
              <div className={`${card} px-[18px] py-4`}>
                <label htmlFor="em" className="text-[15px] font-semibold">
                  Contact email for fetching
                </label>
                <p className="mb-2 text-[13px] text-muted">Put in the User-Agent so site owners can reach you (optional)</p>
                <input id="em" type="email" value={v.CONTACT_EMAIL} onChange={(e) => set("CONTACT_EMAIL", e.target.value)} placeholder="you@example.com" className="w-80 max-w-full rounded border border-border bg-background px-3 py-2.5 text-sm outline-none focus:border-accent" />
              </div>
            </>
          )}

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button type="button" onClick={onSave} disabled={busy || !dirty} className={primary}>
              Save settings
            </button>
            <button type="button" onClick={onReset} disabled={busy} className={ghost}>
              Reset to defaults
            </button>
            {saved && !saved.ok && <span className="max-w-xl text-sm text-danger">{saved.text}</span>}
            {dirty && <span className="text-sm text-muted">Unsaved changes</span>}
          </div>
        </div>
      </div>
    </div>
  );
}
