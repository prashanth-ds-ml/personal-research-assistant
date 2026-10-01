import { NextResponse } from "next/server";
import { getRun, validRunId } from "@/lib/runs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

type Ctx = { params: Promise<{ id: string }> };

// GET: one run with its event timeline, for the live progress page.
export async function GET(_request: Request, ctx: Ctx) {
  const { id } = await ctx.params;
  if (!validRunId(id)) return NextResponse.json({ error: "Invalid run id" }, { status: 400 });
  const run = await getRun(id);
  if (!run) return NextResponse.json({ error: "Run not found" }, { status: 404 });
  return NextResponse.json(run);
}
