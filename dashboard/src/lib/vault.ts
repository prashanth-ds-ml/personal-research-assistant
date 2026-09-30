import fs from "node:fs/promises";
import path from "node:path";
import matter from "gray-matter";

const VAULT_PATH = process.env.VAULT_PATH ?? "";
const RESEARCH_SUBDIR = process.env.RESEARCH_SUBDIR ?? "Research";
const PROFILE_NOTE_PATH = process.env.PROFILE_NOTE_PATH ?? "Profile.md";

export interface ResearchNote {
  slug: string;
  title: string;
  date: string;
  topicSlug: string;
  loops: number;
  sourcesCount: number;
  status: string;
  content: string;
  mtimeMs?: number;
  feedbackRating?: "up" | "down";
  feedbackNote?: string;
}

// A report's file name without ".md". Slugs come from the URL, so they are checked before they touch a path.
const SLUG_RE = /^[\w.-]+$/;

/** Absolute path of a report, or null if the slug is not a plain file name or would leave the Research folder. */
function reportPath(slug: string): string | null {
  if (!VAULT_PATH || !SLUG_RE.test(slug) || slug.includes("..")) return null;
  const dir = path.resolve(VAULT_PATH, RESEARCH_SUBDIR);
  const file = path.resolve(dir, `${slug}.md`);
  return file.startsWith(dir + path.sep) ? file : null;
}

async function pathExists(p: string): Promise<boolean> {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

/** YAML turns an unquoted 2026-09-30 into a Date; the UI wants the plain string. */
function asDateString(value: unknown): string {
  if (value instanceof Date) return value.toISOString().slice(0, 10);
  return typeof value === "string" ? value : "";
}

function feedbackOf(data: Record<string, unknown>): Pick<ResearchNote, "feedbackRating" | "feedbackNote"> {
  const r = data.feedback_rating;
  return {
    feedbackRating: r === "up" || r === "down" ? r : undefined,
    feedbackNote: typeof data.feedback_note === "string" ? data.feedback_note : undefined,
  };
}

function toNote(slug: string, raw: string, mtimeMs?: number): ResearchNote {
  const { data, content } = matter(raw);
  return {
    slug,
    title: typeof data.title === "string" && data.title ? data.title : slug,
    date: asDateString(data.date),
    topicSlug: typeof data.topic_slug === "string" ? data.topic_slug : "",
    loops: typeof data.loops === "number" ? data.loops : 0,
    sourcesCount: typeof data.sources_count === "number" ? data.sources_count : 0,
    status: typeof data.status === "string" ? data.status : "unknown",
    content,
    mtimeMs,
    ...feedbackOf(data),
  };
}

/** Lists all research notes from the vault's Research/ folder, newest first.
 * This is the durable source of truth for research history - deliberately
 * not LangGraph thread history, since the local dev server doesn't persist
 * threads across restarts. A note that cannot be read or parsed (bad YAML after a hand edit in Obsidian)
 * is skipped instead of taking the whole history page down. */
export async function listResearchNotes(): Promise<ResearchNote[]> {
  if (!VAULT_PATH) return [];

  const dir = path.join(VAULT_PATH, RESEARCH_SUBDIR);
  if (!(await pathExists(dir))) return [];

  const files = (await fs.readdir(dir)).filter((f) => f.endsWith(".md"));

  const notes = await Promise.all(
    files.map(async (file) => {
      try {
        const full = path.join(dir, file);
        const [raw, stat] = await Promise.all([fs.readFile(full, "utf-8"), fs.stat(full)]);
        return toNote(file.replace(/\.md$/, ""), raw, stat.mtimeMs);
      } catch {
        return null;
      }
    })
  );

  return notes.filter((n): n is ResearchNote => n !== null).sort((a, b) => (a.date < b.date ? 1 : -1));
}

export async function getResearchNote(slug: string): Promise<ResearchNote | null> {
  const filePath = reportPath(slug);
  if (!filePath || !(await pathExists(filePath))) return null;
  try {
    return toNote(slug, await fs.readFile(filePath, "utf-8"));
  } catch {
    return null;
  }
}

/** Writes the user's rating into the report's frontmatter (same fields the Python planner reads).
 * Returns false if the slug is invalid or the report does not exist. */
export async function saveFeedback(slug: string, rating: "up" | "down", note: string): Promise<boolean> {
  const filePath = reportPath(slug);
  if (!filePath || !(await pathExists(filePath))) return false;
  const { data, content } = matter(await fs.readFile(filePath, "utf-8"));
  data.feedback_rating = rating;
  data.feedback_note = note.trim();
  data.feedback_at = new Date().toISOString();
  await fs.writeFile(filePath, matter.stringify(content, data), "utf-8");
  return true;
}

/** Reads the evolving profile note, or a friendly placeholder if the vault
 * or the note doesn't exist yet (e.g. before the first research run). */
export async function readProfileNote(): Promise<string> {
  if (!VAULT_PATH) {
    return "*No vault configured (set VAULT_PATH in dashboard/.env.local).*";
  }
  const filePath = path.join(VAULT_PATH, PROFILE_NOTE_PATH);
  if (!(await pathExists(filePath))) {
    return "*No profile note yet - run your first research topic to create one.*";
  }
  const raw = await fs.readFile(filePath, "utf-8");
  return matter(raw).content;
}
