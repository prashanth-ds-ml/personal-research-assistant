import { NextResponse } from "next/server";
import { listLibrary } from "@/lib/library";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// GET: how many documents the library holds, by type.
export async function GET() {
  const docs = await listLibrary();
  const n = (k: string) => docs.filter((d) => d.kind === k).length;
  return NextResponse.json({ total: docs.length, pdf: n("pdf"), web: n("web"), hf: n("hf"), doc: n("doc") });
}
