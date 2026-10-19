import { NextResponse } from "next/server";
import { readSettings, writeSettings, SETTING_DEFAULTS, validSetting } from "@/lib/settings";
import { systemStatus } from "@/lib/system";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// GET: the editable settings and the models Ollama has installed. Only the fixed list in lib/settings.ts is ever read.
export async function GET() {
  const [values, sys] = await Promise.all([readSettings(), systemStatus()]);
  return NextResponse.json({ values, defaults: SETTING_DEFAULTS, installed: sys.installed });
}

// POST { changes: { NAME: "value" } } or { reset: true }: write them to .env. JSON only; every value is checked.
export async function POST(request: Request) {
  if (!(request.headers.get("content-type") ?? "").toLowerCase().startsWith("application/json")) {
    return NextResponse.json({ error: "Content-Type must be application/json" }, { status: 415 });
  }
  let body: { changes?: unknown; reset?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Body must be JSON" }, { status: 400 });
  }
  const changes: Record<string, string> = body.reset === true ? { ...SETTING_DEFAULTS } : {};
  if (body.reset !== true && body.changes && typeof body.changes === "object") {
    for (const [k, v] of Object.entries(body.changes as Record<string, unknown>)) {
      if (!validSetting(k, v)) return NextResponse.json({ error: `"${k}" is not a setting you can change, or its value is not allowed.` }, { status: 422 });
      changes[k] = v;
    }
  }
  if (Object.keys(changes).length === 0) return NextResponse.json({ error: "Nothing to save." }, { status: 400 });
  const res = await writeSettings(changes);
  return res.ok ? NextResponse.json({ ok: true }) : NextResponse.json({ error: res.error }, { status: 500 });
}
