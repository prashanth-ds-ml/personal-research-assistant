import { NextResponse, type NextRequest } from "next/server";
import { newJob } from "@/lib/jobs";
import { runScript } from "@/lib/pyrun";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const MAX_URLS = 20;

// POST { urls: string[] }: fetch the pages or PDFs (robots.txt respected, private addresses refused by the fetcher),
// save them under <vault>/Library and index them. Returns a job id at once; poll /api/library/jobs/<id>.
export async function POST(request: NextRequest) {
  let body: { urls?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Bad request" }, { status: 400 });
  }
  const raw = Array.isArray(body.urls) ? body.urls : [];
  const urls: string[] = [];
  for (const u of raw) {
    if (typeof u !== "string") continue;
    const t = u.trim();
    if (!t || t.length > 2000) continue;
    try {
      const p = new URL(t);
      if (p.protocol === "http:" || p.protocol === "https:") urls.push(p.toString());
    } catch {
      /* not a URL: skipped, and counted below */
    }
  }
  const unique = [...new Set(urls)].slice(0, MAX_URLS);
  if (unique.length === 0) return NextResponse.json({ error: "Give at least one web address starting with http:// or https://." }, { status: 400 });

  const job = newJob();
  const args = ["--max", String(unique.length), ...unique.flatMap((u) => ["--seed", u])];
  void runScript("collect.py", args, 30 * 60_000, (line) => {
    job.lines.push(line.slice(0, 300));
    if (job.lines.length > 200) job.lines.shift();
    if (line.startsWith("Result:")) job.summary = line.slice(7).trim();
  }).then((res) => {
    job.status = res.code === 0 ? "done" : "failed";
    if (res.code !== 0) job.summary = res.timedOut ? "Stopped: it took longer than 30 minutes." : res.stderr.trim().split(/\r?\n/).pop() || "The collector failed.";
  });
  return NextResponse.json({ job: job.id, accepted: unique.length, skipped: raw.length - unique.length });
}
