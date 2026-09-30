import { UserCog, Search, Globe, Lightbulb, CheckCircle2 } from "lucide-react";

export type Stage = "profile" | "query" | "research" | "reflect" | "done";

const BASE_STAGES: { key: Stage; label: string; icon: typeof Search }[] = [
  { key: "profile", label: "Loading profile & prior notes", icon: UserCog },
  { key: "query", label: "Generating search query", icon: Search },
  { key: "research", label: "Researching the web", icon: Globe },
  { key: "reflect", label: "Reflecting on knowledge gaps", icon: Lightbulb },
  { key: "done", label: "Report written", icon: CheckCircle2 },
];

export function PipelineStepper({ current }: { current: Stage }) {
  const currentIndex = BASE_STAGES.findIndex((s) => s.key === current);

  return (
    <ol className="flex flex-col gap-1">
      {BASE_STAGES.map((stage, i) => {
        const state = i < currentIndex ? "done" : i === currentIndex ? "active" : "pending";
        const Icon = stage.icon;
        return (
          <li key={stage.key} className="flex items-center gap-3 py-1.5">
            <span
              className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full transition-colors ${
                state === "done"
                  ? "bg-success-soft text-success"
                  : state === "active"
                    ? "bg-accent text-accent-foreground"
                    : "bg-surface-hover text-muted"
              }`}
            >
              <Icon className={`h-3.5 w-3.5 ${state === "active" ? "animate-pulse" : ""}`} />
            </span>
            <span
              className={`text-sm ${
                state === "pending" ? "text-muted" : "font-medium text-foreground"
              }`}
            >
              {stage.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
