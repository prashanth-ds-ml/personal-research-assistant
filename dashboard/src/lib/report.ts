// Turns a deep-research report (markdown written by src/research_assistant/deep_report.py) into parts the magazine reader
// can lay out. Pure functions, no file or network access, so they are easy to test and can never take the page down:
// anything unexpected falls back to "no chapters", and the page then shows the plain report instead.

export type Label = "established" | "single source" | "inference";

export interface StatusRow {
  section: string;
  facts: number;
  docs: number;
  status: string;
}

export interface Chapter {
  num: string;
  title: string;
  /** Markdown, with [E#] cites and [label] tags still in it. */
  body: string;
  /** Evidence ids cited in this chapter, in order, once each. */
  cites: string[];
  /** "ok" has text; "gap" says the library lacked evidence; "failed" means the model could not write it. */
  kind: "ok" | "gap" | "failed";
  facts: number | null;
  docs: number | null;
  status: string;
}

export interface SourceRow {
  group: "pdf" | "web" | "other";
  title: string;
  url: string;
  facts: number;
}

export interface Evidence {
  id: string;
  claim: string;
  quote: string;
  source: string;
}

export interface ParsedReport {
  title: string;
  goal: string;
  status: StatusRow[];
  summary: string;
  chapters: Chapter[];
  limitations: string[];
  sources: SourceRow[];
  evidence: Record<string, Evidence>;
  labelCounts: Record<Label, number>;
}

const ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"];
const META = /^(evidence status|executive summary|limitations|sources|evidence appendix)$/i;
const GAP = /(not enough evidence|does not have enough evidence|no findings were available|could not be assessed|nothing relevant)/i;
const FAILED = /the model failed to write this section/i;

/** Splits a markdown table row on pipes that are not escaped. */
function cells(line: string): string[] {
  const out: string[] = [];
  let cur = "";
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (c === "\\" && line[i + 1] === "|") {
      cur += "|";
      i++;
    } else if (c === "|") {
      out.push(cur.trim());
      cur = "";
    } else {
      cur += c;
    }
  }
  out.push(cur.trim());
  if (out[0] === "") out.shift();
  if (out[out.length - 1] === "") out.pop();
  return out;
}

function tableRows(block: string): string[][] {
  return block
    .split("\n")
    .filter((l) => l.trim().startsWith("|"))
    .map(cells)
    .filter((r) => r.length > 1 && !r.every((c) => /^:?-{2,}:?$/.test(c)))
    .slice(1); // the header row
}

function splitSections(md: string): { title: string; body: string }[] {
  const out: { title: string; body: string }[] = [];
  let cur: { title: string; lines: string[] } | null = null;
  for (const line of md.split("\n")) {
    const m = /^##\s+(.+?)\s*$/.exec(line);
    if (m) {
      if (cur) out.push({ title: cur.title, body: cur.lines.join("\n").trim() });
      cur = { title: m[1], lines: [] };
    } else if (cur) {
      cur.lines.push(line);
    }
  }
  if (cur) out.push({ title: cur.title, body: cur.lines.join("\n").trim() });
  return out;
}

const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

export function citesIn(text: string): string[] {
  const seen: string[] = [];
  for (const m of text.matchAll(/\[(E\d+)\](?!\()/g)) if (!seen.includes(m[1])) seen.push(m[1]);
  return seen;
}

export function countLabels(text: string): Record<Label, number> {
  const count = (re: RegExp) => (text.match(re) ?? []).length;
  return {
    established: count(/\[established\]/g),
    "single source": count(/\[single source\]/g),
    // every flavour of "no real citation" counts as the writer's own inference
    inference: count(/\[inference(?::[^\]]*)?\]/g) + count(/\[cited; (figure|subject) not in the cited evidence\]/g),
  };
}

export function parseReport(markdown: string, fallbackTitle = ""): ParsedReport {
  const h1 = /^#\s+(.+?)\s*$/m.exec(markdown);
  const goal = /^>\s*\*\*Goal:\*\*\s*(.+)$/m.exec(markdown);
  const sections = splitSections(markdown);
  const find = (name: string) => sections.find((s) => s.title.toLowerCase() === name);

  const status: StatusRow[] = tableRows(find("evidence status")?.body ?? "").map((r) => ({
    section: r[0] ?? "",
    facts: Number.parseInt(r[1] ?? "0", 10) || 0,
    docs: Number.parseInt(r[2] ?? "0", 10) || 0,
    status: r[3] ?? "",
  }));

  const evidence: Record<string, Evidence> = {};
  for (const r of tableRows(find("evidence appendix")?.body ?? "")) {
    if (/^E\d+$/.test(r[0] ?? "")) evidence[r[0]] = { id: r[0], claim: r[1] ?? "", quote: (r[2] ?? "").replace(/^"|"$/g, ""), source: r[3] ?? "" };
  }

  const sources: SourceRow[] = [];
  let group: SourceRow["group"] = "other";
  for (const line of (find("sources")?.body ?? "").split("\n")) {
    const g = /^###\s+(.+)$/.exec(line);
    if (g) {
      group = /pdf|paper/i.test(g[1]) ? "pdf" : /web/i.test(g[1]) ? "web" : "other";
      continue;
    }
    const m = /^-\s+(?:\[(.+?)\]\((\S+?)\)|(.+?))\s+-\s+(\d+)\s+fact/.exec(line);
    if (m) {
      sources.push({ group, title: m[1] ?? m[3] ?? "", url: m[2] ?? "", facts: Number.parseInt(m[4], 10) || 0 });
      continue;
    }
    // older reports list sources as plain bullets, with or without a link and with no fact counts
    const plain = /^-\s+(?:\[(.+?)\]\((\S+?)\)|(.+?))\s*$/.exec(line);
    if (plain) sources.push({ group, title: plain[1] ?? plain[3] ?? "", url: plain[2] ?? "", facts: 0 });
  }

  const limitations = (find("limitations")?.body ?? "")
    .split("\n")
    .filter((l) => /^[-*]\s+/.test(l))
    .map((l) => l.replace(/^[-*]\s+/, "").trim());

  const chapters: Chapter[] = [];
  for (const s of sections) {
    if (META.test(s.title)) continue;
    const row = status.find((r) => norm(r.section) === norm(s.title));
    const body = s.body;
    const kind: Chapter["kind"] = FAILED.test(body) ? "failed" : GAP.test(body) && body.length < 600 ? "gap" : "ok";
    chapters.push({
      num: ROMAN[chapters.length] ?? String(chapters.length + 1),
      title: s.title,
      body,
      cites: citesIn(body),
      kind,
      facts: row ? row.facts : null,
      docs: row ? row.docs : null,
      status: row?.status ?? "",
    });
  }

  const summary = find("executive summary")?.body ?? "";
  return {
    title: h1?.[1] ?? fallbackTitle,
    goal: goal?.[1]?.replace(/\s*Clarifications from the user:[\s\S]*$/, "").trim() ?? "",
    status,
    summary,
    chapters,
    limitations,
    sources,
    evidence,
    labelCounts: countLabels(markdown),
  };
}

/** Whole minutes to read, at a calm 220 words a minute. */
export function readMinutes(words: number): number {
  return Math.max(1, Math.round(words / 220));
}

/** Turns [E3] and [label] marks into links the reader draws as margin marks and tags. */
export function markCites(md: string): string {
  return md
    .replace(/\[(E\d+)\](?!\()/g, "[$1](#cite-$1)")
    .replace(/\[(established|single source)\](?!\()/g, (_m, l: string) => `[${l}](#label-${l.replace(" ", "-")})`)
    .replace(/\[cited; (figure|subject) not in the cited evidence\](?!\()/g, (_m, l: string) => `[check ${l}](#label-flag)`)
    .replace(/\[(inference(?::[^\]]*)?)\](?!\()/g, (_m, l: string) => `[${l}](#label-inference)`);
}
