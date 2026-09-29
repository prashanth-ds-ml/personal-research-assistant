import { Handle, Position, type NodeProps } from "@xyflow/react";
import Link from "next/link";

export interface KnowledgeNodeData {
  title: string;
  date: string;
  degree: number;
  [key: string]: unknown;
}

export function KnowledgeNode({ id, data }: NodeProps) {
  const { title, degree } = data as unknown as KnowledgeNodeData;
  const size = Math.min(96, 56 + degree * 10);

  return (
    <Link href={`/research/${id}`}>
      <div
        style={{ width: size, height: size }}
        className="flex items-center justify-center rounded-full border-2 border-accent/50 bg-accent-soft p-2 text-center shadow-sm transition-transform hover:scale-110 hover:border-accent"
      >
        <Handle type="target" position={Position.Top} style={{ opacity: 0 }} />
        <span className="line-clamp-3 text-[10px] font-medium leading-tight text-accent">
          {title}
        </span>
        <Handle type="source" position={Position.Bottom} style={{ opacity: 0 }} />
      </div>
    </Link>
  );
}
