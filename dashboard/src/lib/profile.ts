// Reads the structure of Profile.md (written by src/research_assistant/vault.py). Pure functions: safe in the browser.
export interface SessionEntry {
  date: string;
  title: string;
  /** The bullet lines the assistant wrote for that session. */
  bullets: string[];
}

export const PROFILE_TEMPLATE = `---
title: "Research Assistant Profile"
---
## Standing Preferences

*(Edit this section yourself — the assistant never touches it. Add anything you want every research run to account for: depth level, tone, topics to avoid, etc.)*

## Session Log

*(The assistant appends a dated entry here after each research run. Do not hand-edit; prune old entries in Obsidian if it drifts.)*
`;

/** The text under "## Standing Preferences", without the italic hint line. */
export function standingPreferences(raw: string): string {
  const m = /##\s+Standing Preferences\s*\n([\s\S]*?)(?=\n##\s|$)/.exec(raw);
  return (m?.[1] ?? "").replace(/^\*\(.*\)\*\s*$/gm, "").trim();
}

/** Dated "### date — topic" entries from the Session Log, newest first as stored. */
export function sessionEntries(raw: string): SessionEntry[] {
  const log = /##\s+Session Log\s*\n([\s\S]*)$/.exec(raw)?.[1] ?? "";
  const out: SessionEntry[] = [];
  let cur: SessionEntry | null = null;
  for (const line of log.split("\n")) {
    const h = /^###\s+(\d{4}-\d{2}-\d{2})(?:\s+[—-]\s+(.*))?\s*$/.exec(line);
    if (h) {
      cur = { date: h[1], title: (h[2] ?? "").trim(), bullets: [] };
      out.push(cur);
    } else if (cur && /^[*-]\s+/.test(line)) {
      cur.bullets.push(line.replace(/^[*-]\s+/, "").trim());
    }
  }
  // the assistant sometimes writes two headings in a row (a date, then a dated copy); keep the ones that say something
  return out.filter((e) => e.title || e.bullets.length > 0);
}

/** Distinct topics from the Session Log, for the "topics it has learned from" chips. */
export function topicsOf(entries: SessionEntry[]): string[] {
  const seen = new Set<string>();
  const topics: string[] = [];
  for (const e of entries) {
    const t = e.title.replace(/\?$/, "").trim();
    if (t && !seen.has(t.toLowerCase())) {
      seen.add(t.toLowerCase());
      topics.push(t);
    }
  }
  return topics;
}
