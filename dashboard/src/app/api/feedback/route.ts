import { NextResponse } from "next/server";
import { saveDeskFeedback } from "@/lib/desk";
import { clearFeedback, getResearchNote, saveFeedback } from "@/lib/vault";

/** The report-level rating also goes into the desk database, next to the source and sentence feedback of the same run. */
async function mirror(slug: string, rating: "helpful" | "not_helpful" | "cleared", reason: string) {
  try {
    const note = await getResearchNote(slug);
    if (note?.runId) saveDeskFeedback({ runId: note.runId, reportSlug: slug, target: "report", targetRef: slug, rating, reason });
  } catch {
    // the frontmatter copy is saved already; the desk copy must not turn a saved rating into an error
  }
}

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
  await mirror(slug, rating === "up" ? "helpful" : "not_helpful", text);
  return NextResponse.json({ ok: true });
}

// DELETE { slug }: forget the rating and note left on a report.
export async function DELETE(request: Request) {
  if (!(request.headers.get("content-type") ?? "").toLowerCase().startsWith("application/json")) {
    return NextResponse.json({ error: "Content-Type must be application/json" }, { status: 415 });
  }
  let body: { slug?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Body must be JSON" }, { status: 400 });
  }
  if (typeof body.slug !== "string" || !/^[\w.-]+$/.test(body.slug)) {
    return NextResponse.json({ error: "Invalid report slug" }, { status: 400 });
  }
  const ok = await clearFeedback(body.slug);
  if (ok) await mirror(body.slug, "cleared", "");
  return ok ? NextResponse.json({ ok: true }) : NextResponse.json({ error: "Report not found" }, { status: 404 });
}
