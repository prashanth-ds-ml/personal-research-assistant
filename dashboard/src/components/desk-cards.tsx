"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { SystemStatus } from "@/lib/system";
import type { RunSummary } from "@/lib/runs";
import { useToast } from "@/components/toast";

interface Summary {
  total: number;
  pdf: number;
  web: number;
  hf: number;
  doc: number;
}

const card = "border border-border border-t-4 bg-surface p-6";
const label = "text-[11px] font-semibold uppercase tracking-[0.14em] text-muted";

/** The right-hand column of the Brief screen: what is on the desk, whether this machine is ready, who is waiting. */
export function DeskCards({ onAnswer }: { onAnswer: (runId: string) => void }) {
  const toast = useToast();
  const [lib, setLib] = useState<Summary | null>(null);
  const [sys, setSys] = useState<SystemStatus | null>(null);
  const [waiting, setWaiting] = useState<RunSummary | null>(null);
  const [busy, setBusy] = useState(false);

  const loadSys = async () => {
    try {
      const r = await fetch("/api/system", { cache: "no-store" });
      if (r.ok) setSys((await r.json()) as SystemStatus);
    } catch {
      /* keep what we had */
    }
  };

  useEffect(() => {
    let alive = true;
    fetch("/api/library/summary", { cache: "no-store" })
      .then((r) => r.json())
      .then((b: Summary) => alive && setLib(b))
      .catch(() => undefined);
    fetch("/api/runs", { cache: "no-store" })
      .then((r) => r.json())
      .then((b: { runs: RunSummary[] }) => alive && setWaiting(b.runs.find((x) => x.status === "waiting") ?? null))
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- first reading of the machine
    void loadSys();
    return () => {
      alive = false;
    };
  }, []);

  const free = async () => {
    setBusy(true);
    try {
      const r = await fetch("/api/system/free", { method: "POST" });
      const b = (await r.json()) as { unloaded: string[]; freeGb: number };
      toast("success", `Unloaded ${b.unloaded.length} model${b.unloaded.length === 1 ? "" : "s"}. ${b.freeGb} GB free.`);
      await loadSys();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      <Link href="/library" className={`${card} border-t-foreground text-left hover:shadow-lg`}>
        <div className={label}>On the desk today</div>
        <div className="mt-2 font-serif text-6xl leading-none">{lib ? lib.total : "—"}</div>
        <div className="text-sm text-muted">documents in your library · open the library →</div>
        {lib && (
          <div className="mt-3 text-sm leading-relaxed">
            <b>{lib.pdf}</b> PDFs · <b>{lib.web}</b> web pages · <b>{lib.hf}</b> Hugging Face · <b>{lib.doc}</b> local
          </div>
        )}
      </Link>

      <div className={`${card} border-t-accent`}>
        <div className={label}>Before you begin</div>
        <div className="mt-2 font-serif text-3xl leading-tight">Plan 30 to 60 minutes</div>
        {sys ? (
          <div className="mt-3">
            {[
              { ok: sys.engine, text: sys.engine ? "The research engine is running" : "The research engine is not running. Start it with: langgraph dev" },
              { ok: sys.ollama, text: sys.ollama ? `Ollama running, ${sys.installed.length} models installed` : "Ollama is not running. Start it, then reload." },
              { ok: sys.enoughMemory, text: `Memory: ${sys.freeGb} GB free. Long runs want about 6 GB` },
            ].map((r) => (
              <div key={r.text} className="flex gap-3 border-t border-border py-2 text-sm">
                <span className={`mt-0.5 text-[11px] ${r.ok ? "text-success" : "text-warning"}`} aria-hidden>
                  ●
                </span>
                {r.text}
              </div>
            ))}
            {!sys.enoughMemory && sys.loaded.length > 0 && (
              <button type="button" onClick={free} disabled={busy} className="mt-3 w-full rounded border border-foreground px-4 py-2 text-sm font-semibold hover:bg-foreground hover:text-background disabled:opacity-40">
                {busy ? "Unloading..." : "Unload idle models to free memory"}
              </button>
            )}
          </div>
        ) : (
          <div className="mt-3 text-sm text-muted">Checking this machine...</div>
        )}
      </div>

      {waiting && (
        <div className={`${card} border-t-warning`}>
          <div className={label}>Waiting for you</div>
          <div className="mb-2 mt-2 font-serif text-xl leading-snug">{waiting.goal.split("\n")[0].slice(0, 110)}</div>
          <button type="button" onClick={() => onAnswer(waiting.id)} className="text-sm font-semibold text-accent hover:underline">
            {waiting.waitingFor === "clarify" ? "Answer its questions" : waiting.waitingFor === "review" ? "Choose the sources" : "Approve the plan"} →
          </button>
        </div>
      )}

      <Link href="/knowledge" className="border border-border bg-surface p-5 text-sm leading-relaxed hover:shadow-lg">
        <b>Knowledge graph</b>
        <br />
        Your reports linked to the sources behind them →
      </Link>
    </div>
  );
}
