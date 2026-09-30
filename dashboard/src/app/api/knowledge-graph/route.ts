import { NextResponse } from "next/server";
import { listResearchNotes } from "@/lib/vault";
import { embedText, cosineSimilarity } from "@/lib/embeddings";

export const runtime = "nodejs";

const TOP_K = 3;
const MIN_SIMILARITY = 0.3;
const CONCURRENCY = 3; // embedding calls in flight at once: more just makes Ollama swap models

// Embeddings per note, keyed by slug and the file's modification time: a note is embedded once, not on every
// visit, and only changed notes are embedded again.
const cache = new Map<string, { key: string; embedding: number[] }>();

async function embedAll(notes: Awaited<ReturnType<typeof listResearchNotes>>) {
  const queue = notes.filter((n) => cache.get(n.slug)?.key !== `${n.slug}:${n.mtimeMs}`);
  let next = 0;
  const workers = Array.from({ length: Math.min(CONCURRENCY, queue.length) }, async () => {
    while (next < queue.length) {
      const note = queue[next++];
      const embedding = await embedText(`${note.title}\n\n${note.content}`);
      cache.set(note.slug, { key: `${note.slug}:${note.mtimeMs}`, embedding });
    }
  });
  await Promise.all(workers);
  return notes.map((n) => cache.get(n.slug)!.embedding);
}

export async function GET() {
  const notes = await listResearchNotes();
  if (notes.length === 0) {
    return NextResponse.json({ nodes: [], edges: [] });
  }

  let embeddings: number[][];
  try {
    embeddings = await embedAll(notes);
  } catch (e) {
    // Say what is wrong instead of letting the page claim there are no notes.
    return NextResponse.json(
      { error: "Could not compute note embeddings. Is Ollama running with the embedding model pulled?", detail: String(e).slice(0, 200) },
      { status: 502 }
    );
  }

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
