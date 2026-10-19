"use client";

import { useEffect, useState } from "react";
import type { SystemStatus } from "@/lib/system";

/** One line in the masthead: is the model server up, which model is loaded, how much memory is free. */
export function MemoryChip() {
  const [s, setS] = useState<SystemStatus | null>(null);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const res = await fetch("/api/system", { cache: "no-store" });
        if (res.ok && alive) setS((await res.json()) as SystemStatus);
      } catch {
        /* keep the last reading */
      }
    };
    load();
    const t = setInterval(load, 30000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);

  if (!s) return <span className="hidden text-xs text-muted lg:inline">Checking this machine...</span>;
  const bad = !s.ollama;
  const warn = !bad && !s.enoughMemory;
  const dot = bad ? "text-danger" : warn ? "text-warning" : "text-success";
  const working = s.loaded.find((m) => !/embed/i.test(m));
  const text = bad ? "Ollama is not running" : `${working ?? "models idle"} · ${s.freeGb} GB free${warn ? " (low)" : ""}`;
  return (
    <span className="hidden items-center gap-1.5 text-xs text-muted lg:flex" title="Local model server and free memory">
      <span className={dot} aria-hidden>
        ●
      </span>
      {text}
    </span>
  );
}
