import { RunsWorkspace } from "@/components/runs-workspace";

export const dynamic = "force-dynamic";

export default async function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <RunsWorkspace initialId={id} />;
}
