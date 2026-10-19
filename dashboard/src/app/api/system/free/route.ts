import { NextResponse } from "next/server";
import { unloadModels } from "@/lib/system";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// POST: ask the local model server to drop every loaded model from memory (they reload on next use).
// Safe during a run too: Ollama reloads a model the next time it is called, it is just slower for that call.
export async function POST() {
  return NextResponse.json(await unloadModels());
}
