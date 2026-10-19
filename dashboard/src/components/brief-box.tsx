"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

/** The big "what shall we look into?" box on the front page. It hands the goal to the Research page, which asks the
 * clarifying questions. Nothing runs until you press Begin there. */
export function BriefBox({ compact = false }: { compact?: boolean }) {
  const router = useRouter();
  const [goal, setGoal] = useState("");
  const go = () => {
    if (goal.trim()) router.push(`/deep?goal=${encodeURIComponent(goal.trim())}`);
  };
  return (
    <div>
      <textarea
        value={goal}
        onChange={(e) => setGoal(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) go();
        }}
        aria-label="Your research goal"
        placeholder="Write it as you would brief a colleague, for example: what do practitioners recommend for chunking documents in RAG systems?"
        className={`w-full resize-none border-0 border-b-2 border-foreground bg-transparent py-1.5 font-serif leading-snug outline-none placeholder:text-muted focus:border-accent ${compact ? "h-16 text-xl" : "h-28 text-2xl"}`}
      />
      <div className="mt-4 flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={go}
          disabled={!goal.trim()}
          className="rounded bg-accent px-6 py-3 text-[15px] font-semibold text-accent-foreground disabled:cursor-not-allowed disabled:opacity-55"
        >
          Begin research →
        </button>
        <span className="text-sm text-muted">Ctrl Enter also begins. You approve the plan before any long work starts.</span>
      </div>
    </div>
  );
}
