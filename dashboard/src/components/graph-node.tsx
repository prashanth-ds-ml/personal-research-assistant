import { Handle, Position, type NodeProps } from "@xyflow/react";
import {
  UserCog,
  BookOpen,
  Search,
  Globe,
  FileText,
  Lightbulb,
  CheckCircle2,
  Bell,
  Play,
  Square,
  ListTree,
  Users,
  type LucideIcon,
} from "lucide-react";

const ICONS: Record<string, LucideIcon> = {
  __start__: Play,
  __end__: Square,
  load_profile: UserCog,
  retrieve_vault_context: BookOpen,
  plan_research: ListTree,
  generate_query: Search,
  web_research: Globe,
  summarize_sources: FileText,
  reflect_on_summary: Lightbulb,
  parallel_research: Users,
  finalize_summary: CheckCircle2,
  update_profile: UserCog,
  notify_complete: Bell,
};

const LABELS: Record<string, string> = {
  __start__: "Start",
  __end__: "End",
};

export function GraphNode({ id }: NodeProps) {
  const Icon = ICONS[id] ?? FileText;
  const isTerminal = id === "__start__" || id === "__end__";
  const label = LABELS[id] ?? id.replace(/_/g, " ");

  return (
    <div
      className={`flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-medium shadow-sm ${
        isTerminal
          ? "border-border bg-surface-hover text-muted"
          : "border-border bg-surface text-foreground"
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-border" />
      <span
        className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-full ${
          isTerminal ? "bg-border text-muted" : "bg-accent-soft text-accent"
        }`}
      >
        <Icon className="h-3.5 w-3.5" />
      </span>
      <span className="capitalize">{label}</span>
      <Handle type="source" position={Position.Bottom} className="!bg-border" />
    </div>
  );
}
