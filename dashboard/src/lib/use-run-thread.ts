"use client";

import { useCallback, useEffect, useState } from "react";

/**
 * Remembers the current LangGraph thread in localStorage so a long run survives the user leaving
 * the page (clicking History, closing the tab) and is picked up again when they come back.
 *
 * Without this the page's stream is torn down on navigation and the server cancels the run
 * ("User interrupted the run"). Pair it with `onDisconnect: "continue"` + `streamResumable: true`
 * on submit and `reconnectOnMount: true` on useStream.
 *
 * Each goal gets its own thread: call `forget()` to start a new one. A thread is never reused for
 * a second goal, because graph state (evidence, sources) accumulates on a thread.
 */
export function useRunThread(storageKey: string) {
  const [threadId, setThreadId] = useState<string | null>(null);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(storageKey);
      // eslint-disable-next-line react-hooks/set-state-in-effect -- reading browser-only storage after mount
      if (saved) setThreadId(saved);
    } catch {
      /* storage unavailable (private window): the run still works, it just is not remembered */
    }
  }, [storageKey]);

  const remember = useCallback(
    (id: string) => {
      setThreadId(id);
      try {
        window.localStorage.setItem(storageKey, id);
      } catch {
        /* see above */
      }
    },
    [storageKey]
  );

  const forget = useCallback(() => {
    setThreadId(null);
    try {
      window.localStorage.removeItem(storageKey);
    } catch {
      /* see above */
    }
  }, [storageKey]);

  return { threadId, remember, forget };
}
