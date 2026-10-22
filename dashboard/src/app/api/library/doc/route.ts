import { NextResponse, type NextRequest } from "next/server";
import { isIndexed } from "@/lib/library";
import { runScript } from "@/lib/pyrun";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// POST { action: "reindex" | "remove", id }: re-index one document, or take it out of the library.
// The id must be a document the index already holds; the script checks again that it sits inside a library folder.
export async function POST(request: NextRequest) {
  let body: { action?: unknown; id?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ ok: false, error: "Bad request" }, { status: 400 });
  }
  const action = body.action === "reindex" || body.action === "remove" ? body.action : null;
  const id = typeof body.id === "string" ? body.id : "";
  if (!action || !id || id.length > 600) return NextResponse.json({ ok: false, error: "Bad request" }, { status: 400 });
  if (!isIndexed(id)) return NextResponse.json({ ok: false, error: "That document is not in the library." }, { status: 404 });

  const res = await runScript("library_doc.py", [action, id], 180_000);
  const last = res.stdout.trim().split(/\r?\n/).pop() ?? "";
  try {
    const out = JSON.parse(last) as { ok?: boolean; error?: string };
    return NextResponse.json(out, { status: out.ok ? 200 : 422 });
  } catch {
    const why = res.timedOut ? "It took too long and was stopped." : res.stderr.trim().split(/\r?\n/).pop() || "The script did not answer.";
    return NextResponse.json({ ok: false, error: why }, { status: 500 });
  }
}
