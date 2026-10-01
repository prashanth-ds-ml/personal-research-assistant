import { NextResponse } from "next/server";
import { listRuns } from "@/lib/runs";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// GET: every deep-research run, newest first, read from the vault (survives backend restarts).
export async function GET() {
  return NextResponse.json({ runs: await listRuns() });
}
