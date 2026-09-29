import { NextResponse } from "next/server";
import { listResearchNotes } from "@/lib/vault";
import { embedText, cosineSimilarity } from "@/lib/embeddings";

export const runtime = "nodejs";

const TOP_K = 3;
const MIN_SIMILARITY = 0.3;

export async function GET() {
  const notes = await listResearchNotes();
  if (notes.length === 0) {
    return NextResponse.json({ nodes: [], edges: [] });
  }

  const embeddings = await Promise.all(
    notes.map((note) => embedText(`${note.title}\n\n${note.content}`))
  );

  const edgeSet = new Map<string, { source: string; target: string; weight: number }>();

  for (let i = 0; i < notes.length; i++) {
    const similarities = notes
      .map((_, j) => ({ j, sim: i === j ? -1 : cosineSimilarity(embeddings[i], embeddings[j]) }))
      .filter((s) => s.sim >= MIN_SIMILARITY)
      .sort((a, b) => b.sim - a.sim)
      .slice(0, TOP_K);

    for (const { j, sim } of similarities) {
      const key = [notes[i].slug, notes[j].slug].sort().join("::");
      const existing = edgeSet.get(key);
      if (!existing || sim > existing.weight) {
        edgeSet.set(key, { source: notes[i].slug, target: notes[j].slug, weight: sim });
      }
    }
  }

  return NextResponse.json({
    nodes: notes.map((n) => ({
      id: n.slug,
      title: n.title,
      date: n.date,
      sourcesCount: n.sourcesCount,
    })),
    edges: Array.from(edgeSet.values()),
  });
}
