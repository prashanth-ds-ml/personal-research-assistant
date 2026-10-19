"use client";

import { useState } from "react";

type Kind = "code" | "model" | "pause";
// [id, title, kind, what it does, reads, writes, model, typical time on this machine]
type Step = [string, string, Kind, string, string, string, string, string];

// The step ids are the node names of the two LangGraph graphs in src/research_assistant (goal_graph.py and graph.py).
const DEEP: Step[] = [
  ["refresh_library", "Check library", "code", "Indexes any new or changed files in your library folders so a dropped-in PDF is searchable without running a script.", "Library folders (Sources, Library)", "Search index", "none (embeddings only)", "seconds when nothing changed"],
  ["make_questions", "Write questions", "model", "Writes up to four clarifying questions that would change the research.", "Your goal, titles in the library", "Questions", "qwen3.5:4b", "10 to 20 s"],
  ["clarify", "Ask you", "pause", 'Shows the questions and waits. Blank answers mean "decide for me".', "Questions", "Your answers", "none", "as long as you take"],
  ["plan", "Plan", "model", "Turns the goal into sub-questions and a report outline that always ends with recommendations.", "Goal, answers, feedback on earlier reports", "Plan", "qwen3.5:4b", "10 to 100 s"],
  ["coverage", "Check coverage", "model", "For each question, judges the best passages: covered, thin or nothing. Cheap compared with an hour of wasted work.", "Plan, library", "Coverage per question", "qwen3.5:4b", "1 to 4 min"],
  ["approve", "Approve plan", "pause", "Shows the plan with coverage and waits. You can ask for changes (up to two) and choose what to collect.", "Plan, coverage", "Decision, collect choice", "none", "as long as you take"],
  ["discover", "Find sources", "model", "Searches the web, arXiv, Hugging Face and AI-engineering sites for each chosen question, and judges every result 0 to 3. Downloads nothing.", "Questions to search", "Candidate list", "qwen3.5:4b + search", "2 to 5 min"],
  ["review", "You choose", "pause", "Lists candidates, PDFs and papers apart from web pages. You tick what to keep.", "Candidates", "Your selection", "none", "as long as you take"],
  ["collect", "Collect", "code", "Fetches the chosen sources one at a time, converts them to markdown (Docling for PDFs), saves them with provenance and indexes them.", "Selection", "Library files, manifest", "none (Docling)", "20 s per PDF"],
  ["research", "Gather passages", "model", "Retrieves passages per question (keyword + meaning search) and keeps the ones the model judges useful for that question. Saves progress after every question.", "Plan, library", "Useful passages", "qwen3.5:4b", "1 to 2 min per question"],
  ["write", "Write report", "model", "Writes each section from its own passages only (150-300 words); thin sections become honest gap notes; code flags any number or model name that is not in the cited passage.", "Passages, plan", "Report text", "qwen3.5:4b", "1 to 3 min per section"],
  ["save", "Save", "code", "Saves the report to your vault with its evidence appendix and records the run.", "Report", "Markdown note, run record", "none", "seconds"],
];

const QUICK: Step[] = [
  ["load_profile", "Load profile", "code", "Reads what the assistant has learned about you.", "Profile note", "Profile text", "none", "instant"],
  ["retrieve_vault_context", "Recall notes", "model", "Finds earlier notes in your vault related to the topic.", "Vault", "Related notes", "embeddings", "seconds"],
  ["plan_research", "Plan", "model", "Decides whether the topic is a comparison and splits it into entities.", "Topic", "Plan", "llama3.1:8b", "10 s"],
  ["generate_query", "Make a query", "model", "Writes the next search query.", "Topic, summary so far", "Query", "llama3.1:8b", "5 s"],
  ["web_research", "Search", "code", "Searches the web (or your own documents) and archives the pages.", "Query", "Search results", "none", "5 to 20 s"],
  ["summarize_sources", "Summarise", "model", "Merges the new results into a running summary.", "Results, summary", "Summary", "llama3.1:8b", "20 to 60 s"],
  ["reflect_on_summary", "Reflect", "model", "Finds a knowledge gap and loops back until the loop limit is reached.", "Summary", "Next query", "llama3.1:8b", "10 s"],
  ["finalize_summary", "Finalise", "code", "Assembles the note with its sources.", "Summary", "Note", "none", "instant"],
  ["update_profile", "Update profile", "model", "Adds what was learned about your interests to the profile, append only.", "Note", "Profile", "llama3.1:8b", "10 s"],
  ["notify_complete", "Notify", "code", "Shows a desktop notification.", "Note", "Toast", "none", "instant"],
];

const TONE: Record<Kind, { text: string; border: string; dot: string; tag: string }> = {
  pause: { text: "text-warning", border: "border-warning", dot: "bg-warning", tag: "Waits for you" },
  model: { text: "text-info", border: "border-info", dot: "bg-info", tag: "Local model" },
  code: { text: "text-muted", border: "border-muted", dot: "bg-muted", tag: "Code" },
};

const label = "text-[11px] font-semibold uppercase tracking-widest text-muted";

export default function PipelinePage() {
  const [tab, setTab] = useState<"deep" | "quick">("deep");
  const [sel, setSel] = useState<string | null>(null);
  const steps = tab === "deep" ? DEEP : QUICK;
  const cur = steps.find((s) => s[0] === sel) ?? null;
  const pauses = steps.filter((s) => s[2] === "pause").length;

  return (
    <div className="grid min-h-[calc(100vh-9rem)] gap-0 lg:grid-cols-[minmax(0,1fr)_360px]">
      <div className="min-w-0 lg:pr-9">
        <div className="flex flex-wrap items-end gap-4">
          <div>
            <div className="kicker">How an issue is made</div>
            <h1 className="mt-1 text-5xl leading-none">Pipeline graph</h1>
          </div>
          <div className="flex-1" />
          {(
            [
              ["deep", "Deep research"],
              ["quick", "Quick research"],
            ] as const
          ).map(([k, l]) => (
            <button
              key={k}
              type="button"
              aria-pressed={tab === k}
              onClick={() => {
                setTab(k);
                setSel(null);
              }}
              className={`rounded px-4 py-2 text-sm font-semibold ${tab === k ? "bg-accent-soft text-accent ring-1 ring-accent" : "border border-border hover:border-accent"}`}
            >
              {l}
            </button>
          ))}
        </div>
        <p className="mb-6 mt-3 text-sm text-muted">
          {tab === "deep"
            ? `${steps.length} steps, ${pauses} of which stop and wait for you. The run is saved at every step, so you can leave and come back.`
            : `${steps.length} steps that loop through search and reflection, then write a short note.`}
        </p>
        <div className="flex flex-wrap items-center gap-x-1.5 gap-y-3">
          {steps.map((s, i) => {
            const t = TONE[s[2]];
            return (
              <div key={s[0]} className="flex items-center gap-1.5">
                <button
                  type="button"
                  onClick={() => setSel(s[0])}
                  aria-pressed={sel === s[0]}
                  className={`min-w-[150px] border bg-surface px-3.5 py-3 text-left ${sel === s[0] ? "border-2 border-accent" : `${t.border} border-l-[5px]`}`}
                >
                  <span className={`block text-xs font-semibold ${t.text}`}>{t.tag}</span>
                  <span className="mt-0.5 block text-[15px] font-semibold">{s[1]}</span>
                  <span className="block font-mono text-[11.5px] opacity-65">{s[0]}</span>
                </button>
                {i < steps.length - 1 && (
                  <span className="text-lg text-muted" aria-hidden>
                    →
                  </span>
                )}
              </div>
            );
          })}
        </div>
        <div className="mt-7 flex flex-wrap gap-5 text-[13px]">
          {(["pause", "model", "code"] as Kind[]).map((k) => (
            <span key={k} className="flex items-center gap-2">
              <span className={`inline-block h-2.5 w-2.5 rounded-full ${TONE[k].dot}`} />
              {k === "pause" ? "pauses and waits for you" : k === "model" ? "uses a local model" : "plain code, no model"}
            </span>
          ))}
        </div>
      </div>

      <aside className="mt-8 h-fit border border-border border-t-4 border-t-accent bg-surface p-6 lg:mt-0">
        {!cur ? (
          <>
            <div className={label}>No step selected</div>
            <p className="mt-2 text-[15px] leading-relaxed">Click any step to see what it reads, what it writes, which model runs it and how long it usually takes on this machine.</p>
          </>
        ) : (
          <>
            <div className={label}>{TONE[cur[2]].tag}</div>
            <div className="mb-1 mt-2 font-serif text-3xl leading-tight">{cur[1]}</div>
            <div className="font-mono text-[12.5px] text-muted">{cur[0]}</div>
            <p className="my-4 text-[15px] leading-relaxed">{cur[3]}</p>
            {(
              [
                ["Reads", cur[4]],
                ["Writes", cur[5]],
                ["Model", cur[6]],
                ["Typical time", cur[7]],
              ] as const
            ).map(([k, v]) => (
              <div key={k} className="mb-3">
                <div className={label}>{k}</div>
                <div className="mt-1 text-sm leading-snug">{v}</div>
              </div>
            ))}
            {cur[2] === "pause" && (
              <div className="mt-3 border border-warning bg-warning-soft p-3.5 text-sm leading-relaxed text-warning">
                This step <b>pauses the run</b> until you answer. Leave the page and come back: the run waits.
              </div>
            )}
            <button type="button" onClick={() => setSel(null)} className="mt-4 w-full rounded border border-foreground px-4 py-2.5 text-sm font-semibold hover:bg-foreground hover:text-background">
              Deselect
            </button>
          </>
        )}
      </aside>
    </div>
  );
}
