"use client";

import { useEffect, useState } from "react";
import { ReactFlow, Background, Controls, type Node, type Edge } from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide } from "d3-force";
import { Network } from "lucide-react";
import { KnowledgeNode, type KnowledgeNodeData } from "@/components/knowledge-node";

interface RawNode {
  id: string;
  title: string;
  date: string;
  sourcesCount: number;
}
interface RawEdge {
  source: string;
  target: string;
  weight: number;
}

const nodeTypes = { knowledge: KnowledgeNode };

export default function KnowledgePage() {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [loading, setLoading] = useState(true);
  const [count, setCount] = useState(0);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/knowledge-graph", { signal: controller.signal })
      .then(async (res) => {
        const body = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(body.error ?? `The server answered ${res.status}`);
        return body;
      })
      .then((graph: { nodes: RawNode[]; edges: RawEdge[] }) => {
        setCount(graph.nodes.length);
        if (graph.nodes.length === 0) {
          setLoading(false);
          return;
        }

        const degree = new Map<string, number>();
        for (const e of graph.edges) {
          degree.set(e.source, (degree.get(e.source) ?? 0) + 1);
          degree.set(e.target, (degree.get(e.target) ?? 0) + 1);
        }

        type SimNode = { id: string; x?: number; y?: number };
        const simNodes: SimNode[] = graph.nodes.map((n) => ({ id: n.id }));
        const simLinks = graph.edges.map((e) => ({ ...e }));

        const sim = forceSimulation(simNodes)
          .force("charge", forceManyBody().strength(-300))
          .force(
            "link",
            forceLink(simLinks as never)
              .id((d: unknown) => (d as SimNode).id)
              .distance(120)
          )
          .force("center", forceCenter(0, 0))
          .force("collide", forceCollide(60))
          .stop();

        for (let i = 0; i < 300; i++) sim.tick();

        setNodes(
          graph.nodes.map((n) => {
            const simNode = simNodes.find((s) => s.id === n.id)!;
            return {
              id: n.id,
              type: "knowledge",
              position: { x: simNode.x ?? 0, y: simNode.y ?? 0 },
              data: {
                title: n.title,
                date: n.date,
                degree: degree.get(n.id) ?? 0,
              } satisfies KnowledgeNodeData,
            };
          })
        );
        setEdges(
          graph.edges.map((e, i) => ({
            id: `${e.source}-${e.target}-${i}`,
            source: e.source,
            target: e.target,
            type: "straight",
            style: { stroke: "var(--accent)", opacity: Math.max(0.15, e.weight), strokeWidth: 1 + e.weight * 2 },
          }))
        );
        setLoading(false);
      })
      .catch((e: unknown) => {
        if (controller.signal.aborted) return; // the page was left: nothing to show
        setError(e instanceof Error ? e.message : "Could not load the knowledge graph");
        setLoading(false);
      });
    return () => controller.abort();
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Knowledge Graph</h1>
        <p className="mt-1 text-sm text-muted">
          Your research notes, connected by embedding similarity - the same retrieval your
          assistant uses to build on prior work, visualized.
        </p>
      </div>

      <div className="h-[70vh] w-full overflow-hidden rounded-2xl border border-border bg-surface shadow-sm">
        {loading ? (
          <div className="flex h-full items-center justify-center text-sm text-muted">
            Computing embeddings...
          </div>
        ) : error ? (
          <div role="alert" className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
            <Network className="h-8 w-8 text-warning" />
            <p className="text-sm text-warning">{error}</p>
          </div>
        ) : count === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <Network className="h-8 w-8 text-muted" />
            <p className="text-sm text-muted">
              No research notes yet - the graph fills in as you research.
            </p>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            fitView
            proOptions={{ hideAttribution: true }}
            nodesDraggable
            elementsSelectable={false}
          >
            <Background gap={24} color="var(--border)" />
            <Controls showInteractive={false} />
          </ReactFlow>
        )}
      </div>
    </div>
  );
}
