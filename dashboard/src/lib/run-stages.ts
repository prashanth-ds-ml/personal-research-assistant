// The pipeline as the user thinks of it: seven stages. Each backend step belongs to one stage. Safe in the browser.
export const STAGES = ["Library", "Questions", "Plan", "Sources", "Evidence", "Writing", "Saved"] as const;

export const STAGE_OF: Record<string, number> = {
  library: 0, questions: 1, clarify: 1, plan: 2, approve: 2, coverage: 2, discover: 3, review: 3, collect: 3, research: 4, write: 5, save: 6, done: 7,
};

/** 0-based stage index for a run step (a finished run counts as 7). */
export const stageOf = (step: string, done = false): number => (done ? 7 : (STAGE_OF[step] ?? 0));
