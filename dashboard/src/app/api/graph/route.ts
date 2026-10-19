import { NextResponse } from "next/server";
import { buildGraph } from "@/lib/graph";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// GET: the knowledge graph (reports and the library documents they cite).
export async function GET() {
  return NextResponse.json(await buildGraph());
}
