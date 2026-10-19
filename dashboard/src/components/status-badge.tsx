const STYLES: Record<string, string> = {
  complete: "bg-success-soft text-success",
  running: "bg-warning-soft text-warning",
  unknown: "bg-surface-hover text-muted",
};

export function StatusBadge({ status }: { status: string }) {
  const style = STYLES[status] ?? STYLES.unknown;
  return (
    <span
      className={`rounded px-2 py-0.5 text-[11px] font-medium capitalize ${style}`}
    >
      {status}
    </span>
  );
}
