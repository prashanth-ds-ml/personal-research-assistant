// Compares two deep-research issues. Pure functions over parsed reports, so they are testable and cannot throw on
// an older report that lacks an evidence table or a sources list.
import type { ParsedReport } from "./report.ts";

export interface IssueFacts {
  title: string;
  goal: string;
  date: string;
  words: number;
  facts: number;
  sources: number;
  report: ParsedReport;
}

const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
const words = (s: string) => new Set(norm(s).split(" ").filter((w) => w.length > 2));

/** True when two issues answer the same question: same goal, or titles that share most of their words. */
export function sameTopic(a: { title: string; goal: string }, b: { title: string; goal: string }): boolean {
  if (a.goal && b.goal && norm(a.goal) === norm(b.goal)) return true;
  const x = words(a.title);
  const y = words(b.title);
  if (x.size === 0 || y.size === 0) return false;
  let shared = 0;
  x.forEach((w) => {
    if (y.has(w)) shared++;
  });
  return shared / Math.min(x.size, y.size) >= 0.6;
}

export interface ChapterDiff {
  title: string;
  before: number | null;
  after: number | null;
  /** "new", "dropped", "more", "less", "same" */
  change: "new" | "dropped" | "more" | "less" | "same";
}

export interface Comparison {
  stats: { label: string; before: number; after: number }[];
  chapters: ChapterDiff[];
  addedSources: string[];
  droppedSources: string[];
  recommendation: { before: string; after: string; changed: boolean } | null;
}

const firstSentence = (md: string): string => {
  const plain = md.replace(/\[(E\d+|established|single source|inference[^\]]*)\]/g, "").replace(/[*_>#`]/g, " ").replace(/\s+/g, " ").trim();
  const m = /^(.+?[.!?])(\s|$)/.exec(plain);
  return (m ? m[1] : plain).slice(0, 240);
};

export function compareIssues(a: IssueFacts, b: IssueFacts): Comparison {
  const chaptersA = new Map(a.report.chapters.map((c) => [norm(c.title), c]));
  const chaptersB = new Map(b.report.chapters.map((c) => [norm(c.title), c]));
  const diffs: ChapterDiff[] = [];
  chaptersB.forEach((cb, key) => {
    const ca = chaptersA.get(key);
    const after = cb.facts;
    if (!ca) diffs.push({ title: cb.title, before: null, after, change: "new" });
    else {
      const before = ca.facts;
      const change = before === null || after === null || before === after ? "same" : after > before ? "more" : "less";
      diffs.push({ title: cb.title, before, after, change });
    }
  });
  chaptersA.forEach((ca, key) => {
    if (!chaptersB.has(key)) diffs.push({ title: ca.title, before: ca.facts, after: null, change: "dropped" });
  });

  const titlesA = new Map(a.report.sources.map((s) => [norm(s.title), s.title]));
  const titlesB = new Map(b.report.sources.map((s) => [norm(s.title), s.title]));
  const added = [...titlesB].filter(([k]) => !titlesA.has(k)).map(([, v]) => v);
  const dropped = [...titlesA].filter(([k]) => !titlesB.has(k)).map(([, v]) => v);

  const rec = (r: ParsedReport) => r.chapters.find((c) => /recommend/i.test(c.title) && c.kind === "ok");
  const ra = rec(a.report);
  const rb = rec(b.report);
  const recommendation = ra && rb ? { before: firstSentence(ra.body), after: firstSentence(rb.body), changed: norm(firstSentence(ra.body)) !== norm(firstSentence(rb.body)) } : null;

  const written = (r: ParsedReport) => r.chapters.filter((c) => c.kind === "ok").length;
  return {
    stats: [
      { label: "Verified facts", before: a.facts, after: b.facts },
      { label: "Sources", before: a.sources, after: b.sources },
      { label: "Chapters written", before: written(a.report), after: written(b.report) },
      { label: "Honest gaps", before: a.report.chapters.length - written(a.report), after: b.report.chapters.length - written(b.report) },
    ],
    chapters: diffs,
    addedSources: added,
    droppedSources: dropped,
    recommendation,
  };
}
