import { buildGraph } from "@/lib/graph";
import { KnowledgeGraph } from "@/components/knowledge-graph";

export const dynamic = "force-dynamic";

export default async function KnowledgePage() {
  const { nodes, edges } = await buildGraph();
  return <KnowledgeGraph nodes={nodes} edges={edges} />;
}
