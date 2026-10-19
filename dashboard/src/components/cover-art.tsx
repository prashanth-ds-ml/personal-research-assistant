// Generated cover art: a pattern of blocks, like a document cut into pieces. It is deterministic, so a report keeps
// the same cover, and it grows with the report's evidence, so a thin report looks sparse and a rich one looks busy.

function hash(text: string): number {
  let h = 2166136261;
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

function rng(seed: number) {
  let x = seed || 1;
  return () => {
    x = (Math.imul(x, 1664525) + 1013904223) >>> 0;
    return x / 4294967296;
  };
}

const COLORS = ["var(--accent)", "var(--foreground)", "var(--muted)", "var(--border)", "var(--foreground)"];
const HERO = ["var(--accent)", "#ffffff", "#3a4e68", "#3a4e68", "#5b7090"];

export function CoverArt({
  seed,
  facts = 12,
  hero = false,
  className = "",
}: {
  seed: string;
  facts?: number;
  /** Light blocks for a dark (ink) background. */
  hero?: boolean;
  className?: string;
}) {
  const rnd = rng(hash(seed));
  const palette = hero ? HERO : COLORS;
  const count = Math.max(8, Math.min(30, 8 + Math.round(facts / 3)));
  const blocks = Array.from({ length: count }, (_, i) => {
    const w = 18 + Math.floor(rnd() * (hero ? 120 : 80));
    const h = hero ? 18 : 12;
    return {
      key: i,
      x: Math.floor(rnd() * (300 - w)),
      y: Math.floor(rnd() * (120 - h)),
      w,
      h,
      fill: palette[Math.floor(rnd() * palette.length)],
      opacity: 0.5 + rnd() * 0.45,
    };
  });
  return (
    <svg viewBox="0 0 300 120" preserveAspectRatio="xMidYMid slice" aria-hidden className={className}>
      {blocks.map((b) => (
        <rect key={b.key} x={b.x} y={b.y} width={b.w} height={b.h} rx={2} style={{ fill: b.fill, opacity: b.opacity }} />
      ))}
    </svg>
  );
}
