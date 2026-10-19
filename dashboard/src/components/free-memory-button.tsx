"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useToast } from "@/components/toast";

/** Unloads idle models from memory, then refreshes the page so the readiness card shows the new free memory. */
export function FreeMemoryButton({ loaded }: { loaded: string[] }) {
  const router = useRouter();
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const run = async () => {
    setBusy(true);
    setMsg("");
    try {
      const res = await fetch("/api/system/free", { method: "POST" });
      const body = (await res.json()) as { unloaded: string[]; freeGb: number };
      toast("success", `Unloaded ${body.unloaded.length} model${body.unloaded.length === 1 ? "" : "s"}. ${body.freeGb} GB free.`);
      router.refresh();
    } catch {
      toast("error", "Could not reach the model server.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={run}
        disabled={busy || loaded.length === 0}
        className="w-full rounded border border-foreground px-4 py-2 text-sm font-semibold hover:bg-foreground hover:text-background disabled:opacity-40"
      >
        {busy ? "Unloading..." : loaded.length ? `Unload ${loaded.join(", ")} to free memory` : "No model is loaded; memory is held by other programs"}
      </button>
      {msg && <div className="mt-2 text-xs font-semibold text-success">{msg}</div>}
    </div>
  );
}
