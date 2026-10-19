import { NextResponse } from "next/server";
import { PROFILE_TEMPLATE } from "@/lib/profile";
import { writeProfileRaw } from "@/lib/vault";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// POST { action: "save", text } or { action: "reset" }. JSON only (a plain form or a no-CORS request cannot send it).
// The old note is always kept beside it as Profile.md.bak-<date>.
export async function POST(request: Request) {
  if (!(request.headers.get("content-type") ?? "").toLowerCase().startsWith("application/json")) {
    return NextResponse.json({ error: "Content-Type must be application/json" }, { status: 415 });
  }
  let body: { action?: unknown; text?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Body must be JSON" }, { status: 400 });
  }
  if (body.action === "reset") {
    return NextResponse.json({ ok: await writeProfileRaw(PROFILE_TEMPLATE) });
  }
  if (body.action === "save" && typeof body.text === "string" && body.text.length <= 200_000) {
    // keep the two headings the assistant appends to; without them it would start a second log section
    if (!/##\s+Session Log/.test(body.text) || !/##\s+Standing Preferences/.test(body.text)) {
      return NextResponse.json({ error: 'The note must keep the "## Standing Preferences" and "## Session Log" headings.' }, { status: 422 });
    }
    return NextResponse.json({ ok: await writeProfileRaw(body.text) });
  }
  return NextResponse.json({ error: "Bad request" }, { status: 400 });
}
