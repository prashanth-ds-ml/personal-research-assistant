import fs from "node:fs/promises";
import path from "node:path";
import { DatabaseSync } from "node:sqlite";

// The library is the index the research graph searches: a SQLite file the Python side owns
// (<vault>/.kb/library.sqlite, or KB_PATH). This module only READS it. Adding, re-indexing and removing go through
// the Python scripts (see lib/pyrun.ts), so there is exactly one writer.
const VAULT_PATH = process.env.VAULT_PATH ?? "";

import type { DocKind, LibraryDoc } from "@/lib/library-types";

export type { DocKind, LibraryDoc };

export function kbPath(): string {
  return process.env.KB_PATH || (VAULT_PATH ? path.join(VAULT_PATH, ".kb", "library.sqlite") : "");
}

const hostOf = (url: string): string => {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "";
  }
};

/** A readable title for a document the index only knows by file name ("12-techbytes-app"). */
function prettyName(file: string): string {
  const name = file.replace(/\.(md|pdf)$/i, "").replace(/^\d{4}-\d{5}v\d+-/, "").replace(/^\d{2}-/, "");
  const text = name.replace(/[-_]+/g, " ").trim();
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : file;
}

function prettyFolder(folder: string): string {
  return folder.replace(/^\d{4}-\d{2}-\d{2}-/, "").replace(/-/g, " ");
}

/** The title from the front matter at the top of the saved markdown, when there is one. */
function frontTitle(head: string): string {
  const m = /^title:\s*(.+)$/m.exec(head);
  if (!m) return "";
  return m[1].trim().replace(/^'(.*)'$/, "$1").replace(/^"(.*)"$/, "$1").replace(/''/g, "'");
}

const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

/** Facts each source supplied to finished reports, from the run records (<vault>/.runs). Empty after a clean start. */
async function factsUsed(): Promise<{ byUrl: Map<string, number>; byTitle: Map<string, number> }> {
  const byUrl = new Map<string, number>();
  const byTitle = new Map<string, number>();
  if (!VAULT_PATH) return { byUrl, byTitle };
  const dir = path.join(VAULT_PATH, ".runs");
  let files: string[] = [];
  try {
    files = (await fs.readdir(dir)).filter((f) => f.endsWith(".json") && !f.endsWith(".evidence.json"));
  } catch {
    return { byUrl, byTitle };
  }
  for (const f of files) {
    try {
      const rec = JSON.parse(await fs.readFile(path.join(dir, f), "utf-8")) as { sources?: { title?: string; url?: string; facts?: number }[] };
      for (const s of rec.sources ?? []) {
        const n = typeof s.facts === "number" ? s.facts : 0;
        if (s.url) byUrl.set(s.url, (byUrl.get(s.url) ?? 0) + n);
        if (s.title) byTitle.set(norm(s.title), (byTitle.get(norm(s.title)) ?? 0) + n);
      }
    } catch {
      /* a half-written record is skipped */
    }
  }
  return { byUrl, byTitle };
}

function open(): DatabaseSync | null {
  const p = kbPath();
  if (!p) return null;
  try {
    return new DatabaseSync(p, { readOnly: true });
  } catch {
    return null;
  }
}

export async function listLibrary(): Promise<LibraryDoc[]> {
  const db = open();
  if (!db) return [];
  try {
    const rows = db
      .prepare("SELECT path, title, source_url, n_chunks, status, error, source_kind, ingested_at, substr(markdown, 1, 800) AS head FROM docs ORDER BY ingested_at DESC")
      .all();
    const { byUrl, byTitle } = await factsUsed();
    return rows.map((r) => {
      const key = String(r.path);
      const parts = key.split("/");
      const folder = parts.length > 2 ? parts[1] : "";
      const url = String(r.source_url ?? "");
      const host = hostOf(url);
      const sk = String(r.source_kind ?? "");
      const kind: DocKind = sk === "pdf" || sk === "paper" ? "pdf" : /huggingface\.co$/.test(host) ? "hf" : sk === "web" || url ? "web" : "doc";
      const stem = String(r.title ?? "") || parts[parts.length - 1];
      const title = frontTitle(String(r.head ?? "")) || (/^\d{1,3}-[a-z0-9-]+$/i.test(stem) || /\.(md|pdf)$/i.test(stem) ? prettyName(stem) : stem);
      return {
        id: key,
        title,
        kind,
        site: host || (kind === "doc" ? "your documents" : prettyFolder(folder) || parts[0]),
        url,
        added: String(r.ingested_at ?? "").slice(0, 10),
        folder,
        chunks: Number(r.n_chunks ?? 0),
        facts: (url ? byUrl.get(url) : undefined) ?? byTitle.get(norm(title)) ?? 0,
        status: String(r.status ?? "ok"),
        error: String(r.error ?? ""),
      };
    });
  } catch {
    return [];
  } finally {
    db.close();
  }
}

/** The first part of a document's text for the preview pane, read from the index (front matter removed). */
export async function readPreview(id: string): Promise<string | null> {
  const db = open();
  if (!db) return null;
  try {
    const row = db.prepare("SELECT markdown FROM docs WHERE path = ?").get(id);
    const md = typeof row?.markdown === "string" ? row.markdown : "";
    if (!md) return null;
    const body = md.replace(/^---\n[\s\S]*?\n---\n?/, "").replace(/!\[[^\]]*\]\([^)]*\)/g, "").replace(/\s+\n/g, "\n").trim();
    return body.slice(0, 900) || null;
  } catch {
    return null;
  } finally {
    db.close();
  }
}

/** True when the key is a document in the index. Used to refuse anything else before a script is started. */
export function isIndexed(id: string): boolean {
  const db = open();
  if (!db) return false;
  try {
    return db.prepare("SELECT 1 AS x FROM docs WHERE path = ?").get(id) !== undefined;
  } catch {
    return false;
  } finally {
    db.close();
  }
}
