import { NextResponse } from "next/server";
import { listResearchNotes } from "@/lib/vault";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// GET: a light list of reports (no bodies), for the search palette.
export async function GET() {
  const notes = await listResearchNotes();
  return NextResponse.json({
    reports: notes.map(({ slug, title, date, kind }) => ({ slug, title, date, kind })),
  });
}
