import { listResearchNotes } from "@/lib/vault";
import { listLibrary } from "@/lib/library";
import { parseReport } from "@/lib/report";
import type { DocKind } from "@/lib/library-types";

// The knowledge graph: reports and the library documents behind them. A report links to a document when the
// report's own Sources list names it (by address, or by title). Nothing here is guessed from similarity.
export type NodeKind = "report" | DocKind;

export interface GraphNode {
  id: string;
  kind: NodeKind;
  title: string;
  /** Host name, or the report's date. */
  site: string;
  url: string;
  /** Verified facts (reports) or facts the reports used from it (documents). */
  facts: number;
  /** Where "open" goes: the report page, or the library row. */
  slug?: string;
  docId?: string;
}

export interface GraphEdge {
  source: string;
  target: string;
}

const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
const normUrl = (u: string) => u.replace(/^https?:\/\/(www\.)?/i, "").replace(/[#?].*$/, "").replace(/\/+$/, "").toLowerCase();

export async function buildGraph(): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
  const [notes, docs] = await Promise.all([listResearchNotes(), listLibrary()]);
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];

  const byUrl = new Map<string, string>();
  const byTitle = new Map<string, string>();
  for (const d of docs) {
    const id = `d:${d.id}`;
    nodes.push({ id, kind: d.kind, title: d.title, site: d.site, url: d.url, facts: d.facts, docId: d.id });
    if (d.url) byUrl.set(normUrl(d.url), id);
    byTitle.set(norm(d.title), id);
  }

  for (const n of notes) {
    const id = `r:${n.slug}`;
    nodes.push({ id, kind: "report", title: n.title, site: n.date, url: "", facts: n.evidence, slug: n.slug });
    const seen = new Set<string>();
    for (const s of parseReport(n.content, n.title).sources) {
      const target = (s.url && byUrl.get(normUrl(s.url))) || byTitle.get(norm(s.title));
      if (target && !seen.has(target)) {
        seen.add(target);
        edges.push({ source: id, target });
      }
    }
  }
  return { nodes, edges };
}
