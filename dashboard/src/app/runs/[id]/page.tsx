import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { RunView } from "@/components/run-view";

export const dynamic = "force-dynamic";

export default async function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="flex flex-col gap-6">
      <Link href="/runs" className="flex w-fit items-center gap-1.5 text-sm text-muted hover:text-foreground">
        <ArrowLeft className="h-3.5 w-3.5" />
        All runs
      </Link>
      <h1 className="text-2xl font-semibold tracking-tight">Run progress</h1>
      <RunView id={id} />
    </div>
  );
}
