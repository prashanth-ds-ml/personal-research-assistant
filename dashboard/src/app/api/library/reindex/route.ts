import { NextResponse } from "next/server";
import path from "node:path";
import { newJob } from "@/lib/jobs";
import { runScript } from "@/lib/pyrun";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// POST { mode: "refresh" | "rebuild" }: index new or changed files in the library folders ("refresh"), or rebuild every
// vector from the saved text after the embedding model changed ("rebuild"). Returns a job id; poll /api/library/jobs/<id>.
export async function POST(request: Request) {
  let body: { mode?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Bad request" }, { status: 400 });
  }
  const vault = process.env.VAULT_PATH ?? "";
  if (!vault) return NextResponse.json({ error: "VAULT_PATH is not set." }, { status: 400 });
  const job = newJob();
  const args = body.mode === "rebuild" ? ["--rebuild"] : [path.join(vault, "Sources"), path.join(vault, "Library")];
  const script = body.mode === "rebuild" ? "reindex.py" : "ingest_library.py";
  void runScript(script, args, 60 * 60_000, (line) => {
    job.lines.push(line.slice(0, 300));
    if (job.lines.length > 200) job.lines.shift();
  }).then((res) => {
    job.status = res.code === 0 ? "done" : "failed";
    job.summary = res.code === 0 ? job.lines[job.lines.length - 1] ?? "Done." : res.timedOut ? "Stopped: it took longer than an hour." : res.stderr.trim().split(/\r?\n/).pop() || "The script failed.";
  });
  return NextResponse.json({ job: job.id });
}
