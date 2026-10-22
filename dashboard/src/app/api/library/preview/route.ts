import { NextResponse, type NextRequest } from "next/server";
import { readPreview } from "@/lib/library";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// GET ?id=<document key>: the first part of a document's text. The key is looked up in the index, never used as a path.
export async function GET(request: NextRequest) {
  const id = request.nextUrl.searchParams.get("id") ?? "";
  if (!id || id.length > 600) return NextResponse.json({ text: null }, { status: 400 });
  return NextResponse.json({ text: await readPreview(id) });
}
