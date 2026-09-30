import { NextResponse } from "next/server";
import { saveFeedback } from "@/lib/vault";

export const runtime = "nodejs";

// POST { slug, rating: "up" | "down", note?: string }
// Stored in the report's own frontmatter (feedback_rating / feedback_note / feedback_at) - the same
// fields the Python side reads to tell the planner what worked - so the vault stays the source of truth.
//
// Requires Content-Type: application/json. A plain HTML form or a no-CORS request cannot send that (it
// would need a preflight, which this server never approves), so another website cannot write feedback.
// (src/proxy.ts additionally refuses foreign Hosts and Origins.)
export async function POST(request: Request) {
  if (!(request.headers.get("content-type") ?? "").toLowerCase().startsWith("application/json")) {
    return NextResponse.json({ error: "Content-Type must be application/json" }, { status: 415 });
  }

  let body: { slug?: unknown; rating?: unknown; note?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Body must be JSON" }, { status: 400 });
  }

  const { slug, rating, note } = body;
  if (typeof slug !== "string" || !/^[\w.-]+$/.test(slug)) {
    return NextResponse.json({ error: "Invalid report slug" }, { status: 400 });
  }
  if (rating !== "up" && rating !== "down") {
    return NextResponse.json({ error: 'rating must be "up" or "down"' }, { status: 400 });
  }
  const text = typeof note === "string" ? note.slice(0, 1000) : "";

  const ok = await saveFeedback(slug, rating, text);
  if (!ok) return NextResponse.json({ error: "Report not found" }, { status: 404 });
  return NextResponse.json({ ok: true });
}
