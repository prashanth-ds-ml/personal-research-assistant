import { NextResponse } from "next/server";
import { runView } from "@/lib/desk";
import { validRunId } from "@/lib/runs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Ctx = { params: Promise<{ id: string }> };

// GET: what the report page needs from a run's trace: evidence -> library chunk, the report's sentences, current feedback.
export async function GET(_request: Request, ctx: Ctx) {
  const { id } = await ctx.params;
  if (!validRunId(id)) return NextResponse.json({ error: "Invalid run id" }, { status: 400 });
  try {
    const view = runView(id);
    if (!view) return NextResponse.json({ error: "No trace for this run" }, { status: 404 });
    return NextResponse.json(view);
  } catch (e) {
    return NextResponse.json({ error: e instanceof Error ? e.message : "Could not read the trace" }, { status: 500 });
  }
}
