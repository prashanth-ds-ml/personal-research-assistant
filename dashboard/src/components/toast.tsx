"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

type Kind = "success" | "error" | "info";
interface Item {
  id: number;
  kind: Kind;
  text: string;
}

const Ctx = createContext<(kind: Kind, text: string) => void>(() => undefined);

/** Say it where it cannot be missed: a short message at the bottom of the screen that fades by itself. */
export const useToast = () => useContext(Ctx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Item[]>([]);
  const next = useRef(1);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const dismiss = useCallback((id: number) => {
    setItems((l) => l.filter((i) => i.id !== id));
    const t = timers.current.get(id);
    if (t) clearTimeout(t);
    timers.current.delete(id);
  }, []);

  const push = useCallback(
    (kind: Kind, text: string) => {
      const id = next.current++;
      setItems((l) => [...l.slice(-3), { id, kind, text }]);
      // errors stay longer: they usually need reading twice
      timers.current.set(id, setTimeout(() => dismiss(id), kind === "error" ? 9000 : 5000));
    },
    [dismiss]
  );

  useEffect(() => {
    const live = timers.current;
    return () => live.forEach((t) => clearTimeout(t));
  }, []);

  const tone: Record<Kind, string> = {
    success: "border-l-success",
    error: "border-l-danger",
    info: "border-l-info",
  };

  return (
    <Ctx.Provider value={push}>
      {children}
      <div aria-live="polite" className="no-print pointer-events-none fixed inset-x-0 bottom-5 z-[60] flex flex-col items-center gap-2 px-4">
        {items.map((i) => (
          <div
            key={i.id}
            role={i.kind === "error" ? "alert" : "status"}
            className={`pointer-events-auto flex w-full max-w-md items-start gap-3 rounded border border-l-4 border-border bg-ink px-4 py-3 text-sm leading-snug text-ink-foreground shadow-2xl ${tone[i.kind]}`}
          >
            <span className="flex-1">{i.text}</span>
            <button type="button" onClick={() => dismiss(i.id)} className="text-xs font-semibold text-ink-muted hover:text-white" aria-label="Dismiss">
              ✕
            </button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}
