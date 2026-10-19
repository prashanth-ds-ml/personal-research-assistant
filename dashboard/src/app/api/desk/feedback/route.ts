import { NextResponse } from "next/server";
import { saveDeskFeedback, validFeedback } from "@/lib/desk";

export const runtime = "nodejs";

// POST { runId, target: "chunk" | "sentence" | "section" | "report", targetRef, rating, reason?, section?, reportSlug? }
// Appends one feedback row to the desk database (src/research_assistant/desk_schema.sql). The latest row per target wins;
// rating "cleared" withdraws an earlier one.
//
// Requires Content-Type: application/json, which a plain form or a no-CORS request from another site cannot send
// (src/proxy.ts also refuses foreign Hosts and Origins).
export async function POST(request: Request) {
  if (!(request.headers.get("content-type") ?? "").toLowerCase().startsWith("application/json")) {
    return NextResponse.json({ error: "Content-Type must be application/json" }, { status: 415 });
  }
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Body must be JSON" }, { status: 400 });
  }
  if (!validFeedback(body)) {
    return NextResponse.json({ error: "Invalid feedback: check runId, target, targetRef and rating" }, { status: 400 });
  }
  try {
    const id = saveDeskFeedback(body);
    if (id === null) return NextResponse.json({ error: "VAULT_PATH is not set" }, { status: 500 });
    return NextResponse.json({ ok: true, id });
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "Could not save feedback" }, { status: 500 });
  }
}
