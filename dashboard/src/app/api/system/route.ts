import { NextResponse } from "next/server";
import { systemStatus } from "@/lib/system";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// GET: is the local model server up, which models are loaded, and how much memory is free.
export async function GET() {
  return NextResponse.json(await systemStatus());
}
