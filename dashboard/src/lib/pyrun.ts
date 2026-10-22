import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import path from "node:path";

// Runs one of the project's Python scripts (scripts/*.py) for the dashboard. The arguments are passed as an array
// and no shell is involved, so nothing a user types can become a command. Callers validate their own arguments.
const ROOT = process.env.RESEARCH_ROOT || path.resolve(process.cwd(), "..");

function pythonBin(): string {
  if (process.env.PYTHON_BIN) return process.env.PYTHON_BIN;
  // the project's own venv (`uv sync` creates <repo>/.venv) first, then a venv shared by parent folders
  for (const rel of [".venv/Scripts/python.exe", ".venv/bin/python", "../../.venv/Scripts/python.exe", "../../.venv/bin/python", "../.venv/Scripts/python.exe", "../.venv/bin/python"]) {
    const p = path.resolve(ROOT, rel);
    if (existsSync(p)) return p;
  }
  return "python";
}

export interface PyResult {
  code: number | null;
  stdout: string;
  stderr: string;
  timedOut: boolean;
}

// The dashboard's own settings (its .env.local) must not leak into the Python scripts: they have their own .env, and the
// two files write some names differently (the dashboard's EMBEDDING_MODEL has no "ollama:" prefix). Secrets stay out too.
const DASHBOARD_ONLY = new Set(["LANGGRAPH_API_URL", "LANGSMITH_API_KEY", "LANGSMITH_PROJECT", "VAULT_PATH", "RESEARCH_SUBDIR", "PROFILE_NOTE_PATH", "OLLAMA_BASE_URL", "EMBEDDING_MODEL", "KB_PATH", "LIBRARY_FOLDERS"]);

function scriptEnv(): Record<string, string | undefined> {
  const env: Record<string, string | undefined> = {};
  for (const [k, v] of Object.entries(process.env)) {
    if (DASHBOARD_ONLY.has(k) || k.startsWith("NEXT_") || k.startsWith("__NEXT")) continue;
    env[k] = v;
  }
  return { ...env, PYTHONIOENCODING: "utf-8", PYTHONUNBUFFERED: "1" };
}

export function runScript(script: string, args: string[], timeoutMs: number, onLine?: (line: string) => void): Promise<PyResult> {
  return new Promise((resolve) => {
    const child = spawn(pythonBin(), [path.join(ROOT, "scripts", script), ...args], {
      cwd: ROOT,
      env: scriptEnv() as NodeJS.ProcessEnv,
      windowsHide: true,
      shell: false,
    });
    let stdout = "";
    let stderr = "";
    let timedOut = false;
    let buf = "";
    const timer = setTimeout(() => {
      timedOut = true;
      child.kill();
    }, timeoutMs);
    child.stdout.on("data", (d: Buffer) => {
      const text = d.toString("utf-8");
      stdout += text;
      if (onLine) {
        buf += text;
        const lines = buf.split(/\r?\n/);
        buf = lines.pop() ?? "";
        lines.forEach((l) => l.trim() && onLine(l));
      }
    });
    child.stderr.on("data", (d: Buffer) => {
      stderr += d.toString("utf-8");
    });
    child.on("error", (e) => {
      clearTimeout(timer);
      resolve({ code: null, stdout, stderr: `${stderr}${e.message}`, timedOut });
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      resolve({ code, stdout, stderr, timedOut });
    });
  });
}
