"use client";

import { useEffect, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { GraphNode } from "@/components/graph-node";

const ASSISTANT_ID =
  process.env.NEXT_PUBLIC_LANGGRAPH_ASSISTANT_ID ?? "research_assistant";

const Y_STEP = 90;
const X_CENTER = 200;

const nodeTypes = { pipeline: GraphNode };

export default function GraphPage() {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/api/assistants/${ASSISTANT_ID}/graph`)
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        return res.json();
      })
      .then((graph: { nodes: { id: string }[]; edges: { source: string; target: string; conditional?: boolean }[] }) => {
        setNodes(
          graph.nodes.map((n, i) => ({
            id: n.id,
            type: "pipeline",
            position: { x: X_CENTER, y: i * Y_STEP },
            data: {},
          }))
        );
        setEdges(
          graph.edges.map((e, i) => ({
            id: `${e.source}-${e.target}-${i}`,
            source: e.source,
            target: e.target,
            animated: Boolean(e.conditional),
            style: e.conditional
              ? { strokeDasharray: "4 4", stroke: "var(--accent)" }
              : { stroke: "var(--border)" },
            label: e.source === "reflect_on_summary" && e.target === "web_research" ? "loop" : undefined,
          }))
        );
      })
      .catch((err) => setError(String(err)));
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Graph</h1>
        <p className="mt-1 text-sm text-muted">
          The actual compiled LangGraph structure, fetched live from the local dev server.
        </p>
      </div>

      {error && (
        <p className="text-sm text-warning">
          Couldn&apos;t load the graph - is <code>langgraph dev</code> running? ({error})
        </p>
      )}

      <div className="h-[70vh] w-full overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
        {nodes.length > 0 && (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            proOptions={{ hideAttribution: true }}
            nodesConnectable={false}
            nodesDraggable={true}
            elementsSelectable={false}
          >
            <Background gap={20} color="var(--border)" />
            <Controls showInteractive={false} />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}
