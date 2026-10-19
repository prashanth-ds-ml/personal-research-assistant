import fs from "node:fs/promises";
import path from "node:path";

// The Settings screen edits a short, fixed list of options in the project's .env file. Everything else in that file
// (API keys, paths, service addresses) is never read into the page and never changed: only the lines named below are
// touched, every other line is written back exactly as it was.
const ROOT = process.env.RESEARCH_ROOT || path.resolve(process.cwd(), "..");
const ENV_FILE = process.env.RESEARCH_ENV_FILE || path.join(ROOT, ".env");

export const DEFAULT_SITES = [
  "sebastianraschka.com", "magazine.sebastianraschka.com", "karpathy.github.io", "karpathy.ai", "jalammar.github.io", "newsletter.languagemodels.co",
  "huggingface.co", "github.com", "docs.langchain.com", "anthropic.com", "openai.com", "ai.google.dev", "lilianweng.github.io", "eugeneyan.com",
  "huyenchip.com", "hamel.dev", "simonwillison.net", "pinecone.io",
];

type Spec = { kind: "bool" } | { kind: "int"; min: number; max: number } | { kind: "model" } | { kind: "sites" } | { kind: "email" };

// name -> how to check it, and its default (the one the Python side uses when the line is absent)
const SPECS: Record<string, { spec: Spec; def: string }> = {
  LOCAL_LLM: { spec: { kind: "model" }, def: "llama3.1:8b" },
  WRITER_MODEL: { spec: { kind: "model" }, def: "gemma4:e4b" },
  EMBEDDING_MODEL: { spec: { kind: "model" }, def: "ollama:qwen3-embedding:0.6b" },
  COLLECT_HUGGINGFACE: { spec: { kind: "bool" }, def: "True" },
  COLLECT_AI_SITES: { spec: { kind: "bool" }, def: "True" },
  COLLECT_EUROPEPMC: { spec: { kind: "bool" }, def: "True" },
  FETCH_MAX_SOURCES: { spec: { kind: "int", min: 0, max: 500 }, def: "0" },
  COLLECT_EXTRA_SITES: { spec: { kind: "sites" }, def: DEFAULT_SITES.join(";") },
  COVERAGE_CHECK: { spec: { kind: "bool" }, def: "True" },
  CLAIM_LABELS: { spec: { kind: "bool" }, def: "True" },
  REQUIRE_PLAN_APPROVAL: { spec: { kind: "bool" }, def: "True" },
  ASK_CLARIFYING_QUESTIONS: { spec: { kind: "bool" }, def: "True" },
  MIN_SECTION_FACTS: { spec: { kind: "int", min: 1, max: 20 }, def: "3" },
  MIN_SECTION_DOCUMENTS: { spec: { kind: "int", min: 1, max: 10 }, def: "2" },
  INCLUDE_ARCHIVED_PAGES: { spec: { kind: "bool" }, def: "False" },
  LANGCHAIN_TRACING_V2: { spec: { kind: "bool" }, def: "False" },
  CONTACT_EMAIL: { spec: { kind: "email" }, def: "" },
};

export const SETTING_KEYS = Object.keys(SPECS);
export const SETTING_DEFAULTS: Record<string, string> = Object.fromEntries(SETTING_KEYS.map((k) => [k, SPECS[k].def]));

/** True when the value is acceptable for that setting. Nothing else is ever written. */
export function validSetting(key: string, value: unknown): value is string {
  const s = SPECS[key];
  if (!s || typeof value !== "string" || value.length > 4000 || /[\r\n]/.test(value)) return false;
  switch (s.spec.kind) {
    case "bool":
      return value === "True" || value === "False";
    case "int": {
      const n = Number(value);
      return /^\d+$/.test(value) && n >= s.spec.min && n <= s.spec.max;
    }
    case "model":
      return /^[\w.:/-]{1,100}$/.test(value);
    case "email":
      return value === "" || /^[^\s@;#]+@[^\s@;#]+\.[^\s@;#]+$/.test(value);
    case "sites":
      return value.split(";").every((h) => /^[a-z0-9]([a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}$/.test(h)) && value.split(";").length <= 60;
  }
}

/** The line's value without its trailing "# comment" and surrounding quotes. */
function cleanValue(raw: string): string {
  return raw.replace(/\s+#.*$/, "").trim().replace(/^(['"])(.*)\1$/, "$2");
}

export async function readSettings(): Promise<Record<string, string>> {
  const out: Record<string, string> = { ...SETTING_DEFAULTS };
  let text = "";
  try {
    text = await fs.readFile(ENV_FILE, "utf-8");
  } catch {
    return out; // no .env yet: every setting is at its default
  }
  for (const line of text.split(/\r?\n/)) {
    const m = /^\s*([A-Z0-9_]+)\s*=(.*)$/.exec(line);
    if (!m || !(m[1] in SPECS)) continue; // anything not on the list (keys, paths, urls) is skipped, not read
    const v = cleanValue(m[2]);
    if (v !== "" || SPECS[m[1]].spec.kind === "email") out[m[1]] = v;
  }
  return out;
}

/** Writes the given settings into .env: existing lines are updated in place, new ones are added at the end. */
export async function writeSettings(changes: Record<string, string>): Promise<{ ok: boolean; error?: string }> {
  for (const [k, v] of Object.entries(changes)) {
    if (!validSetting(k, v)) return { ok: false, error: `"${k}" has a value that is not allowed.` };
  }
  let text = "";
  try {
    text = await fs.readFile(ENV_FILE, "utf-8");
  } catch {
    /* a new file */
  }
  const eol = text.includes("\r\n") ? "\r\n" : "\n";
  const lines = text === "" ? [] : text.split(/\r?\n/);
  const done = new Set<string>();
  const next = lines.map((line) => {
    const m = /^(\s*)([A-Z0-9_]+)(\s*=\s*)(.*)$/.exec(line);
    if (!m || !(m[2] in changes)) return line;
    done.add(m[2]);
    return `${m[1]}${m[2]}${m[3]}${changes[m[2]]}`;
  });
  const add = Object.keys(changes).filter((k) => !done.has(k));
  if (add.length > 0) {
    if (next.length > 0 && next[next.length - 1] !== "") next.push("");
    next.push("# Written by the dashboard's Settings screen");
    add.forEach((k) => next.push(`${k}=${changes[k]}`));
  }
  const body = next.join(eol) + (next[next.length - 1] === "" ? "" : eol);
  const tmp = `${ENV_FILE}.tmp`;
  try {
    await fs.writeFile(tmp, body, "utf-8");
    await fs.rename(tmp, ENV_FILE);
  } catch {
    return { ok: false, error: "Could not write the .env file." };
  }
  return { ok: true };
}
