// Small in-memory record of background jobs started from the dashboard (adding sources can take minutes).
// It lives in the server process: after a restart a running job's output is gone, but what it indexed is not.
export interface Job {
  id: string;
  status: "running" | "done" | "failed";
  lines: string[];
  summary: string;
  startedAt: number;
}

const g = globalThis as unknown as { __jobs?: Map<string, Job> };
const jobs = (g.__jobs ??= new Map<string, Job>());

export function newJob(): Job {
  // keep the table small: forget finished jobs older than an hour
  for (const [k, j] of jobs) if (j.status !== "running" && Date.now() - j.startedAt > 3600_000) jobs.delete(k);
  const job: Job = { id: crypto.randomUUID(), status: "running", lines: [], summary: "", startedAt: Date.now() };
  jobs.set(job.id, job);
  return job;
}

export const getJob = (id: string): Job | undefined => jobs.get(id);
