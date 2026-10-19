"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useRef, useState } from "react";
import { forceCenter, forceCollide, forceLink, forceManyBody, forceSimulation, forceX, forceY, type SimulationLinkDatum, type SimulationNodeDatum } from "d3-force";
import type { GraphEdge, GraphNode, NodeKind } from "@/lib/graph";
import { safeHref } from "@/lib/safe-href";
import { useToast } from "@/components/toast";

const KINDS: { key: NodeKind; label: string; color: string }[] = [
  { key: "report", label: "Reports", color: "#ff6a4d" },
  { key: "pdf", label: "PDFs and papers", color: "#6fa8ff" },
  { key: "web", label: "Web pages", color: "#4fd1a5" },
  { key: "hf", label: "Hugging Face", color: "#ffb84d" },
  { key: "doc", label: "Local documents", color: "#8d9bb0" },
];
const COLOR = Object.fromEntries(KINDS.map((k) => [k.key, k.color])) as Record<NodeKind, string>;
const LABEL = Object.fromEntries(KINDS.map((k) => [k.key, k.label])) as Record<NodeKind, string>;

type Sim = SimulationNodeDatum & { id: string };
const W = 1000;
const H = 720;

const label = "text-[11px] font-semibold uppercase tracking-widest text-muted";
const btn = "w-full rounded px-4 py-2.5 text-sm font-semibold";
const primary = `${btn} bg-accent text-accent-foreground hover:opacity-90`;
const ghost = `${btn} border border-foreground hover:bg-foreground hover:text-background`;
const danger = `${btn} border border-danger text-danger hover:bg-danger hover:text-accent-foreground disabled:opacity-40`;

export function KnowledgeGraph({ nodes, edges }: { nodes: GraphNode[]; edges: GraphEdge[] }) {
  const router = useRouter();
  const toast = useToast();
  const [sel, setSel] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [q, setQ] = useState("");
  const [on, setOn] = useState<Record<NodeKind, boolean>>({ report: true, pdf: true, web: true, hf: true, doc: true });
  const [orphans, setOrphans] = useState(true);
  const [labels, setLabels] = useState(true);
  const [size, setSize] = useState(1);
  const [spread, setSpread] = useState(1);
  const [local, setLocal] = useState(false);
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const [confirm, setConfirm] = useState(false);
  const [note, setNote] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const drag = useRef<{ x: number; y: number; vx: number; vy: number; moved: boolean } | null>(null);

  const byId = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes]);
  const degree = useMemo(() => {
    const d = new Map<string, number>();
    edges.forEach((e) => {
      d.set(e.source, (d.get(e.source) ?? 0) + 1);
      d.set(e.target, (d.get(e.target) ?? 0) + 1);
    });
    return d;
  }, [edges]);
  const neighbours = useMemo(() => {
    const m = new Map<string, Set<string>>();
    edges.forEach((e) => {
      (m.get(e.source) ?? m.set(e.source, new Set()).get(e.source)!).add(e.target);
      (m.get(e.target) ?? m.set(e.target, new Set()).get(e.target)!).add(e.source);
    });
    return m;
  }, [edges]);

  // The layout is worked out once per data set and link distance, with a fixed start so it never jumps around.
  const pos = useMemo(() => {
    const sim: Sim[] = nodes.map((n, i) => {
      const a = (i / Math.max(nodes.length, 1)) * Math.PI * 2;
      return { id: n.id, x: W / 2 + Math.cos(a) * 260, y: H / 2 + Math.sin(a) * 260 };
    });
    const links: SimulationLinkDatum<Sim>[] = edges.map((e) => ({ source: e.source, target: e.target }));
    const s = forceSimulation(sim)
      .force("link", forceLink<Sim, SimulationLinkDatum<Sim>>(links).id((d) => d.id).distance(70 * spread).strength(0.6))
      .force("charge", forceManyBody().strength(-70 * spread))
      .force("center", forceCenter(W / 2, H / 2))
      .force("collide", forceCollide(14))
      // gravity keeps unlinked documents near the middle instead of drifting off the canvas
      .force("gx", forceX(W / 2).strength(0.09))
      .force("gy", forceY(H / 2).strength(0.12))
      .stop();
    for (let i = 0; i < 260; i++) s.tick();
    const r1 = (v: number | undefined, d: number) => Math.round((v ?? d) * 10) / 10;
    return new Map(sim.map((n) => [n.id, { x: r1(n.x, W / 2), y: r1(n.y, H / 2) }]));
  }, [nodes, edges, spread]);

  const needle = q.trim().toLowerCase();
  const visible = useMemo(() => {
    const keep = new Set<string>();
    const focus = local && sel ? new Set([sel, ...(neighbours.get(sel) ?? [])]) : null;
    for (const n of nodes) {
      if (!on[n.kind]) continue;
      if (!orphans && !(degree.get(n.id) ?? 0)) continue;
      if (focus && !focus.has(n.id)) continue;
      keep.add(n.id);
    }
    return keep;
  }, [nodes, on, orphans, degree, local, sel, neighbours]);

  const shownEdges = edges.filter((e) => visible.has(e.source) && visible.has(e.target));
  const counts = (k: NodeKind) => nodes.filter((n) => n.kind === k).length;
  const selNode = sel ? byId.get(sel) ?? null : null;
  const hovNode = hover ? byId.get(hover) ?? null : null;
  const related = selNode ? [...(neighbours.get(selNode.id) ?? [])].map((id) => byId.get(id)).filter((n): n is GraphNode => Boolean(n)) : [];
  const reports = nodes.filter((n) => n.kind === "report").length;

  const radius = (n: GraphNode) => (n.kind === "report" ? 9 : 5.5) * size + Math.min(6, (degree.get(n.id) ?? 0) * 0.8);
  const matches = (n: GraphNode) => !needle || `${n.title} ${n.site}`.toLowerCase().includes(needle);
  const zoom = (f: number) => setView((v) => ({ ...v, k: Math.min(3, Math.max(0.3, v.k * f)) }));

  const remove = async () => {
    if (!selNode?.docId) return;
    setBusy(true);
    setConfirm(false);
    try {
      const res = await fetch("/api/library/doc", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ action: "remove", id: selNode.docId }) });
      const body = (await res.json()) as { ok?: boolean; error?: string };
      if (body.ok) {
        setSel(null);
        setNote(null);
        toast("success", "Removed from the library. The file is in the vault's .removed folder.");
        router.refresh();
      } else {
        setNote({ ok: false, text: body.error ?? "That did not work." });
      }
    } catch {
      setNote({ ok: false, text: "Could not reach the dashboard server." });
    } finally {
      setBusy(false);
    }
  };

  if (nodes.length === 0) {
    return (
      <div className="py-10">
        <div className="kicker">The map</div>
        <h1 className="mt-1 text-5xl leading-none">Knowledge graph</h1>
        <p className="mt-6 font-serif text-4xl leading-tight">The map is empty.</p>
        <p className="mt-2 font-serif text-xl italic text-muted">Add sources to the library, or run a deep research, and they will appear here.</p>
        <Link href="/library" className="mt-5 inline-block rounded bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground">
          Open the library
        </Link>
      </div>
    );
  }

  return (
    <div className="grid min-h-[calc(100vh-9rem)] gap-0 border border-border bg-surface lg:grid-cols-[270px_minmax(0,1fr)_340px]">
      {/* left controls */}
      <div className="flex flex-col border-border p-5 lg:border-r">
        <div className="kicker">The map</div>
        <h1 className="mb-4 mt-1 text-4xl leading-none">Knowledge graph</h1>
        <label htmlFor="gq" className={label}>
          Search nodes
        </label>
        <input id="gq" value={q} onChange={(e) => setQ(e.target.value)} placeholder="type a title or site" className="mt-2 w-full rounded border border-border bg-background px-3 py-2 text-sm outline-none focus:border-accent" />
        <div className={`${label} mt-5`}>Filters</div>
        {KINDS.map((k) => (
          <label key={k.key} className="flex cursor-pointer items-center gap-2.5 py-1.5 text-sm">
            <input type="checkbox" checked={on[k.key]} onChange={() => setOn({ ...on, [k.key]: !on[k.key] })} className="accent-accent" />
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: k.color }} />
            <span className="flex-1">{k.label}</span>
            <span className="text-xs text-muted">{counts(k.key)}</span>
          </label>
        ))}
        <label className="flex cursor-pointer items-center gap-2.5 py-1.5 text-sm">
          <input type="checkbox" checked={orphans} onChange={() => setOrphans(!orphans)} className="accent-accent" />
          Show documents no report cites
        </label>
        <div className={`${label} mt-5`}>Display</div>
        <label className="flex cursor-pointer items-center gap-2.5 py-1.5 text-sm">
          <input type="checkbox" checked={labels} onChange={() => setLabels(!labels)} className="accent-accent" /> Show labels
        </label>
        <label htmlFor="gs" className="mt-2 block text-[13px]">
          Node size
        </label>
        <input id="gs" type="range" min="0.7" max="1.6" step="0.1" value={size} onChange={(e) => setSize(Number(e.target.value))} className="w-full accent-accent" />
        <label htmlFor="gd" className="mt-2 block text-[13px]">
          Link distance
        </label>
        <input id="gd" type="range" min="0.6" max="1.5" step="0.05" value={spread} onChange={(e) => setSpread(Number(e.target.value))} className="w-full accent-accent" />
        <label className="flex cursor-pointer items-center gap-2.5 py-3 text-sm">
          <input type="checkbox" checked={local} onChange={() => setLocal(!local)} className="accent-accent" /> Local graph (selected node and its links)
        </label>
        <div className="flex-1" />
        <p className="text-xs leading-relaxed text-muted">A report links to the library documents named in its Sources list. A document several reports cite sits between them.</p>
      </div>

      {/* canvas */}
      <div className="relative min-h-[560px] overflow-hidden bg-ink">
        <div className="absolute right-3.5 top-3.5 z-10 flex flex-col gap-2">
          {[
            { l: "Zoom in", t: "+", f: () => zoom(1.25) },
            { l: "Zoom out", t: "−", f: () => zoom(0.8) },
            { l: "Fit to screen and reset", t: "⌂", f: () => setView({ x: 0, y: 0, k: 1 }) },
          ].map((b) => (
            <button key={b.l} type="button" aria-label={b.l} onClick={b.f} className="h-9 w-9 rounded border border-[#3a4e68] bg-[#101e33] text-lg text-ink-foreground hover:border-white">
              {b.t}
            </button>
          ))}
        </div>
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="h-full w-full cursor-grab touch-none select-none active:cursor-grabbing"
          role="img"
          aria-label="Knowledge graph"
          onWheel={(e) => zoom(e.deltaY < 0 ? 1.1 : 0.9)}
          onPointerDown={(e) => {
            drag.current = { x: e.clientX, y: e.clientY, vx: view.x, vy: view.y, moved: false };
            (e.currentTarget as SVGSVGElement).setPointerCapture(e.pointerId);
          }}
          onPointerMove={(e) => {
            const d = drag.current;
            if (!d) return;
            const dx = e.clientX - d.x;
            const dy = e.clientY - d.y;
            if (Math.abs(dx) + Math.abs(dy) > 3) d.moved = true;
            setView((v) => ({ ...v, x: d.vx + dx, y: d.vy + dy }));
          }}
          onPointerUp={() => {
            drag.current = null;
          }}
          onClick={() => {
            // a click on empty canvas (not the end of a drag) deselects
          }}
        >
          <g transform={`translate(${view.x} ${view.y}) translate(${W / 2} ${H / 2}) scale(${view.k}) translate(${-W / 2} ${-H / 2})`}>
            {shownEdges.map((e) => {
              const a = pos.get(e.source);
              const b = pos.get(e.target);
              if (!a || !b) return null;
              const hot = sel && (e.source === sel || e.target === sel);
              return <line key={`${e.source}-${e.target}`} x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={hot ? "#ff6a4d" : "#3a4e68"} strokeWidth={hot ? 1.8 : 1} opacity={sel && !hot ? 0.35 : 0.8} />;
            })}
            {nodes.filter((n) => visible.has(n.id)).map((n) => {
              const p = pos.get(n.id);
              if (!p) return null;
              const dim = (needle && !matches(n)) || (sel && n.id !== sel && !(neighbours.get(sel)?.has(n.id)));
              return (
                <g key={n.id} opacity={dim ? 0.2 : 1}>
                  <circle
                    cx={p.x}
                    cy={p.y}
                    r={radius(n)}
                    fill={COLOR[n.kind]}
                    stroke={n.id === sel ? "#fff" : "none"}
                    strokeWidth={2}
                    className="cursor-pointer"
                    tabIndex={0}
                    role="button"
                    aria-label={`${LABEL[n.kind]}: ${n.title}`}
                    onPointerDown={(e) => e.stopPropagation()}
                    onClick={(e) => {
                      e.stopPropagation();
                      setSel(n.id === sel ? null : n.id);
                      setConfirm(false);
                      setNote(null);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") setSel(n.id === sel ? null : n.id);
                    }}
                    onMouseEnter={() => setHover(n.id)}
                    onMouseLeave={() => setHover(null)}
                  />
                  {labels && view.k >= 0.8 && (n.kind === "report" || n.id === sel || view.k >= 1.3 || (degree.get(n.id) ?? 0) > 1) && (
                    <text x={p.x} y={p.y + radius(n) + 11} textAnchor="middle" fontSize={10} fill="#ddE5f0" pointerEvents="none">
                      {n.title.length > 26 ? `${n.title.slice(0, 25)}…` : n.title}
                    </text>
                  )}
                </g>
              );
            })}
          </g>
        </svg>
        {hovNode && (
          <div className="pointer-events-none absolute bottom-4 left-4 max-w-sm rounded border border-[#3a4e68] bg-[#101e33] px-3.5 py-2.5 text-sm text-ink-foreground">
            <b>{hovNode.title}</b>
            <div className="text-xs text-ink-muted">
              {LABEL[hovNode.kind]} · {hovNode.site} · {degree.get(hovNode.id) ?? 0} links
            </div>
          </div>
        )}
      </div>

      {/* right details */}
      <div className="border-border p-6 lg:border-l">
        {!selNode ? (
          <>
            <div className={label}>Nothing selected</div>
            <p className="mt-2 text-[15px] leading-relaxed">Click a node. You will see where it came from, how many facts were used, and which reports cite it.</p>
            <div className="mt-5 text-sm leading-[1.9]">
              <b>{nodes.length}</b> nodes · <b>{edges.length}</b> links
              <br />
              <b>{reports}</b> reports · <b>{nodes.length - reports}</b> sources
            </div>
          </>
        ) : (
          <div className="flex flex-col">
            <span className="w-fit rounded px-2.5 py-1 text-xs font-semibold text-[#0c1626]" style={{ background: COLOR[selNode.kind] }}>
              {LABEL[selNode.kind].replace(/s$/, "")}
            </span>
            <div className="mb-1.5 mt-3 font-serif text-2xl leading-snug">{selNode.title}</div>
            <div className="text-[13px] text-muted">{selNode.site}</div>
            <div className="my-4 flex gap-8">
              <div>
                <div className="font-serif text-4xl leading-tight">{selNode.facts}</div>
                <div className="text-[13px] text-muted">facts used</div>
              </div>
              <div>
                <div className="font-serif text-4xl leading-tight">{related.length}</div>
                <div className="text-[13px] text-muted">{selNode.kind === "report" ? "sources" : "reports cite it"}</div>
              </div>
            </div>
            <div className={label}>{selNode.kind === "report" ? "Sources it used" : "Cited by"}</div>
            <div className="mb-4 mt-1 max-h-48 overflow-auto">
              {related.length === 0 && <div className="py-1 text-sm text-muted">{selNode.kind === "report" ? "None of its sources are in the library." : "No report cites it yet."}</div>}
              {related.map((r) => (
                <button key={r.id} type="button" onClick={() => setSel(r.id)} className="block w-full py-1 text-left text-sm text-accent hover:underline">
                  {r.title}
                </button>
              ))}
            </div>
            <div className="flex flex-col gap-2">
              {selNode.slug && (
                <Link href={`/research/${selNode.slug}`} className={`${primary} text-center`}>
                  Open report
                </Link>
              )}
              {selNode.url ? (
                <a href={safeHref(selNode.url)} target="_blank" rel="noopener noreferrer nofollow" className={`${primary} text-center`}>
                  Open original source
                </a>
              ) : (
                selNode.docId && (
                  <a href={`/api/library/file?id=${encodeURIComponent(selNode.docId)}`} target="_blank" rel="noopener noreferrer" className={`${primary} text-center`}>
                    Open the file
                  </a>
                )
              )}
              <button type="button" onClick={() => setLocal(!local)} className={ghost}>
                {local ? "Show the whole graph" : "Show only this node and its links"}
              </button>
              {selNode.docId && (
                <button type="button" onClick={() => setConfirm(true)} disabled={busy} className={danger}>
                  Remove from library
                </button>
              )}
              <button type="button" onClick={() => setSel(null)} className={ghost}>
                Deselect
              </button>
            </div>
            {confirm && (
              <div className="mt-4 border border-danger p-4 text-sm leading-relaxed">
                <b>Remove this source?</b>
                <br />
                It leaves the library and this graph. Reports that cited it keep their quotes. The file moves to the vault&apos;s <code>.removed</code> folder.
                <div className="mt-3 flex gap-2">
                  <button type="button" onClick={remove} className={danger}>
                    Yes, remove
                  </button>
                  <button type="button" onClick={() => setConfirm(false)} className={ghost}>
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
        {note && <div className={`mt-4 border px-4 py-3 text-sm ${note.ok ? "border-success text-success" : "border-danger text-danger"}`}>{note.text}</div>}
      </div>
    </div>
  );
}
