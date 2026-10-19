import os from "node:os";

// What this machine and the local model server are doing right now. Read only, nothing leaves the machine.
const ENGINE = (process.env.LANGGRAPH_API_URL || "http://127.0.0.1:2025").replace(/\/$/, "");
const OLLAMA = (process.env.OLLAMA_BASE_URL || "http://127.0.0.1:11434").replace(/\/$/, "");
/** A long run wants about this much free memory for the writer model. */
export const WANT_FREE_GB = 6;

export interface SystemStatus {
  ollama: boolean;
  /** The research engine (langgraph dev) answers. */
  engine: boolean;
  /** Models installed locally. */
  installed: string[];
  /** Models loaded into memory right now. */
  loaded: string[];
  freeGb: number;
  totalGb: number;
  enoughMemory: boolean;
}

async function getJson<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url, { cache: "no-store", signal: AbortSignal.timeout(1500) });
    return res.ok ? ((await res.json()) as T) : null;
  } catch {
    return null;
  }
}

export async function systemStatus(): Promise<SystemStatus> {
  const [tags, ps, engine] = await Promise.all([
    getJson<{ models?: { name: string }[] }>(`${OLLAMA}/api/tags`),
    getJson<{ models?: { name: string }[] }>(`${OLLAMA}/api/ps`),
    getJson<{ ok?: boolean }>(`${ENGINE}/ok`),
  ]);
  const gb = (bytes: number) => Math.round((bytes / 1024 ** 3) * 10) / 10;
  const freeGb = gb(os.freemem());
  return {
    ollama: tags !== null,
    engine: engine !== null,
    installed: (tags?.models ?? []).map((m) => m.name),
    loaded: (ps?.models ?? []).map((m) => m.name),
    freeGb,
    totalGb: gb(os.totalmem()),
    enoughMemory: freeGb >= WANT_FREE_GB,
  };
}

/** Models a run needs. Override with DASHBOARD_EXPECTED_MODELS (comma separated) if you changed them in .env. */
export const EXPECTED_MODELS = (process.env.DASHBOARD_EXPECTED_MODELS ?? "llama3.1:8b,gemma4:e4b,qwen3-embedding:0.6b")
  .split(",")
  .map((m) => m.trim())
  .filter(Boolean);

/** Tells Ollama to unload every model that is currently in memory (keep_alive 0). They load again when next used. */
export async function unloadModels(): Promise<{ unloaded: string[]; freeGb: number }> {
  const ps = await getJson<{ models?: { name: string }[] }>(`${OLLAMA}/api/ps`);
  const names = (ps?.models ?? []).map((m) => m.name);
  await Promise.all(
    names.map((model) =>
      fetch(`${OLLAMA}/api/generate`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ model, keep_alive: 0 }),
        signal: AbortSignal.timeout(5000),
      }).catch(() => null)
    )
  );
  await new Promise((r) => setTimeout(r, 800));
  return { unloaded: names, freeGb: Math.round((os.freemem() / 1024 ** 3) * 10) / 10 };
}
