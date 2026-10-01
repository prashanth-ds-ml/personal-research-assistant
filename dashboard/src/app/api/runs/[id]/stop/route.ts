import { NextResponse } from "next/server";
import { stopRun, validRunId } from "@/lib/runs";

export const runtime = "nodejs";

type Ctx = { params: Promise<{ id: string }> };

// POST: stop a running run. Needs Content-Type: application/json like /api/feedback, so another website cannot
// trigger it (it would need a preflight this server never approves); src/proxy.ts also refuses foreign origins.
export async function POST(request: Request, ctx: Ctx) {
  if (!(request.headers.get("content-type") ?? "").toLowerCase().startsWith("application/json")) {
    return NextResponse.json({ error: "Content-Type must be application/json" }, { status: 415 });
  }
  const { id } = await ctx.params;
  if (!validRunId(id)) return NextResponse.json({ error: "Invalid run id" }, { status: 400 });
  const result = await stopRun(id);
  return NextResponse.json(result, { status: result.ok ? 200 : 500 });
}
