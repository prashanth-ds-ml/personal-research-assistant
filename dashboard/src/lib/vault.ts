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
}

async function pathExists(p: string): Promise<boolean> {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

/** Lists all research notes from the vault's Research/ folder, newest first.
 * This is the durable source of truth for research history - deliberately
 * not LangGraph thread history, since the local dev server doesn't persist
 * threads across restarts. */
export async function listResearchNotes(): Promise<ResearchNote[]> {
  if (!VAULT_PATH) return [];

  const dir = path.join(VAULT_PATH, RESEARCH_SUBDIR);
  if (!(await pathExists(dir))) return [];

  const files = (await fs.readdir(dir)).filter((f) => f.endsWith(".md"));

  const notes = await Promise.all(
    files.map(async (file) => {
      const raw = await fs.readFile(path.join(dir, file), "utf-8");
      const { data, content } = matter(raw);
      return {
        slug: file.replace(/\.md$/, ""),
        title: data.title ?? file,
        date: data.date ?? "",
        topicSlug: data.topic_slug ?? "",
        loops: data.loops ?? 0,
        sourcesCount: data.sources_count ?? 0,
        status: data.status ?? "unknown",
        content,
      } satisfies ResearchNote;
    })
  );

  return notes.sort((a, b) => (a.date < b.date ? 1 : -1));
}

export async function getResearchNote(slug: string): Promise<ResearchNote | null> {
  if (!VAULT_PATH) return null;
  const filePath = path.join(VAULT_PATH, RESEARCH_SUBDIR, `${slug}.md`);
  if (!(await pathExists(filePath))) return null;

  const raw = await fs.readFile(filePath, "utf-8");
  const { data, content } = matter(raw);
  return {
    slug,
    title: data.title ?? slug,
    date: data.date ?? "",
    topicSlug: data.topic_slug ?? "",
    loops: data.loops ?? 0,
    sourcesCount: data.sources_count ?? 0,
    status: data.status ?? "unknown",
    content,
  };
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
