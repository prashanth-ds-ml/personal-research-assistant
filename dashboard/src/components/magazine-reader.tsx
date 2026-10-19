"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Chapter, Label, ParsedReport, SourceRow } from "@/lib/report";
import { markCites, readMinutes } from "@/lib/report";
import { CoverArt } from "@/components/cover-art";
import { ChunkRating, SentenceFlags, useDesk, type Desk } from "@/components/desk-feedback";

export interface ReaderMeta {
  slug: string;
  title: string;
  date: string;
  words: number;
  facts: number;
  sourcesCount: number;
  obsidianUrl: string;
  /** The run that wrote the report; enables source and sentence feedback ("" for older reports). */
  runId: string;
}

const LABEL_STYLE: Record<Label, string> = {
  established: "bg-success-soft text-success",
  "single source": "bg-surface-hover text-muted",
  inference: "bg-warning-soft text-warning",
};

const tag = "ml-0.5 mr-0.5 inline-block rounded-[3px] px-1.5 py-[3px] align-[2px] font-sans text-[10.5px] font-semibold uppercase leading-none tracking-wider";
const chip = "rounded border border-border px-3 py-1.5 text-xs font-semibold hover:border-accent hover:text-accent";
const chipOn = "rounded border border-accent bg-accent px-3 py-1.5 text-xs font-semibold text-accent-foreground";

/** A chapter's markdown, with [E#] marks as clickable margin marks and sentence labels as small tags. */
function Body({
  text,
  cite,
  onCite,
  focus,
}: {
  text: string;
  cite: string | null;
  onCite: (id: string) => void;
  focus: Label | "";
}) {
  const md = useMemo(() => markCites(text), [text]);
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        img: () => null,
        p: ({ children }) => <p className="mb-[1.05em] hyphens-auto break-inside-avoid-column">{children}</p>,
        ul: ({ children }) => <ul className="mb-[1.05em] list-disc pl-6">{children}</ul>,
        ol: ({ children }) => <ol className="mb-[1.05em] list-decimal pl-6">{children}</ol>,
        h3: ({ children }) => <h3 className="mb-2 mt-5 text-[1.15em]">{children}</h3>,
        table: ({ children }) => (
          <div className="avoid-break my-[1.2em] overflow-x-auto font-sans text-[0.78em] [column-span:all]">
            <table className="w-full border-collapse">{children}</table>
          </div>
        ),
        th: ({ children }) => <th className="border-b-2 border-foreground px-2 py-1 text-left font-semibold">{children}</th>,
        td: ({ children }) => <td className="border-b border-border px-2 py-1 align-top">{children}</td>,
        a: ({ href, children }) => {
          const label = String(children);
          if (href?.startsWith("#cite-")) {
            const id = href.slice(6);
            const on = cite === id;
            return (
              <button
                type="button"
                onClick={() => onCite(id)}
                aria-pressed={on}
                className={`mx-0.5 -translate-y-1 cursor-pointer rounded px-1 font-sans text-[11.5px] font-semibold align-super ${
                  on ? "bg-accent text-accent-foreground" : "text-accent hover:bg-accent-soft"
                }`}
              >
                {label}
              </button>
            );
          }
          if (href === "#label-flag") {
            return <span className={`${tag} bg-danger-soft text-danger`} title="This sentence failed a code check: verify it against the source">{label}</span>;
          }
          if (href?.startsWith("#label-")) {
            const kind: Label = href === "#label-established" ? "established" : href === "#label-single-source" ? "single source" : "inference";
            const dim = focus && focus !== kind;
            return <span className={`${tag} ${LABEL_STYLE[kind]} ${dim ? "opacity-20" : ""} ${focus === kind ? "outline outline-2 outline-accent" : ""}`}>{label.replace(/^inference.*$/, "inference")}</span>;
          }
          return href && /^(https?:|mailto:)/i.test(href) ? (
            <a href={href} target="_blank" rel="noopener noreferrer nofollow" className="text-accent underline">
              {children}
            </a>
          ) : (
            <span>{children}</span>
          );
        },
      }}
    >
      {md}
    </ReactMarkdown>
  );
}

/** A v3 passage starts with its "[document > section]" breadcrumb; the quote is what follows it. */
function passageText(quote: string): string {
  return quote.replace(/^\[[^\]]{0,400}\]\s*/, "");
}

/** "Document › last heading" for a v3 passage (its claim is "title › heading path"); the source title otherwise. */
function whereFrom(ev: { claim: string; source: string }): string {
  if (!ev.claim.includes(" › ")) return ev.source;
  const heading = ev.claim.slice(ev.claim.indexOf(" › ") + 3).split(" > ").pop()?.trim();
  return heading ? `${ev.source} › ${heading}` : ev.source;
}

function EvidenceNotes({ chapter: c, report, cite, look, desk }: { chapter: Chapter; report: ParsedReport; cite: string | null; look: { label: string; cls: string }; desk: Desk }) {
  const [opened, setOpened] = useState<Set<string>>(new Set());
  const flip = (id: string) =>
    setOpened((o) => {
      const n = new Set(o);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  return (
    <div className="space-y-4">
      {c.facts !== null && (
        <div className={`border border-border border-t-[3px] p-4 ${look.label === "no evidence" ? "border-t-accent" : "border-t-foreground"}`}>
          <div className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Evidence</div>
          <div className="mt-1 text-[15px]">
            <b className="font-serif text-3xl">{c.facts ?? "—"}</b> facts · <b className="font-serif text-3xl">{c.docs ?? "—"}</b> documents
          </div>
          <span className={`mt-2 inline-block rounded-[3px] px-2 py-1 text-[11px] font-semibold uppercase tracking-wider ${look.cls}`}>{look.label}</span>
        </div>
      )}
      {c.cites.map((id) => {
        const ev = report.evidence[id];
        if (!ev) return null;
        const on = cite === id;
        const quote = passageText(ev.quote);
        const long = quote.length > 110;
        const full = on || opened.has(id) || !long;
        const text = full ? quote : `${quote.slice(0, 107).trimEnd()}…`;
        return (
          <div key={id} className={`avoid-break border-l-[3px] px-4 py-3 transition-colors ${on ? "border-accent bg-accent-soft" : "border-border"}`}>
            <div className="text-[11px] font-semibold uppercase tracking-[0.12em] text-accent">{id}</div>
            <div className="my-1 font-serif text-[15px] italic leading-snug">
              <span className="print:hidden">&ldquo;{text}&rdquo;</span>
              <span className="hidden print:inline">&ldquo;{quote}&rdquo;</span>
            </div>
            <div className="flex items-start gap-2 text-xs text-muted">
              <span className="min-w-0 flex-1 truncate" title={whereFrom(ev)}>{whereFrom(ev)}</span>
              {long && !on && (
                <button type="button" onClick={() => flip(id)} className="no-print shrink-0 font-semibold text-accent hover:underline">
                  {full ? "less" : "more"}
                </button>
              )}
            </div>
            <ChunkRating desk={desk} eid={id} section={c.title} />
          </div>
        );
      })}
    </div>
  );
}

function statusLook(c: Chapter): { label: string; cls: string } {
  if (c.kind === "gap" || (c.facts === 0 && c.docs === 0)) return { label: "no evidence", cls: "bg-danger-soft text-danger" };
  if (c.kind === "failed") return { label: "not written", cls: "bg-danger-soft text-danger" };
  if (c.facts !== null && c.facts < 3) return { label: "thin", cls: "bg-warning-soft text-warning" };
  return { label: c.status || "supported", cls: "bg-success-soft text-success" };
}

function SourceList({ title, rows, onCopy }: { title: string; rows: SourceRow[]; onCopy: (text: string, done: string) => void }) {
  if (rows.length === 0) return null;
  return (
    <div>
      <div className="border-b border-border pb-2 text-sm font-semibold">
        {title} · {rows.length}
      </div>
      {rows.map((s, i) => (
        <div key={`${s.title}-${i}`} className="flex items-start gap-3 border-b border-border py-3">
          <div className="min-w-0 flex-1">
            {s.url ? (
              <a href={s.url} target="_blank" rel="noopener noreferrer nofollow" className="font-serif text-xl leading-snug hover:text-accent">
                {s.title}
              </a>
            ) : (
              <span className="font-serif text-xl leading-snug">{s.title}</span>
            )}
            {s.facts > 0 && <div className="text-xs text-muted">{s.facts} facts used</div>}
          </div>
          <button
            type="button"
            onClick={() => onCopy(`${s.title}${s.url ? `. ${s.url}` : ""}. Accessed ${new Date().toISOString().slice(0, 10)}.`, "Citation copied.")}
            className="shrink-0 text-xs font-semibold text-accent hover:underline"
          >
            Copy citation
          </button>
        </div>
      ))}
    </div>
  );
}

export function MagazineReader({ report, meta, children }: { report: ParsedReport; meta: ReaderMeta; children?: ReactNode }) {
  const [size, setSize] = useState(20);
  const [cols, setCols] = useState<1 | 2>(2);
  const [faith, setFaith] = useState(false);
  const [focus, setFocus] = useState<Label | "">("");
  const [cite, setCite] = useState<string | null>(null);
  const [sel, setSel] = useState("");
  const [prog, setProg] = useState(0);
  const [toast, setToast] = useState("");
  const article = useRef<HTMLDivElement>(null);
  const desk = useDesk(meta.runId, meta.slug);

  const minutes = readMinutes(meta.words);
  const goalHref = (text: string) => `/deep?goal=${encodeURIComponent(text)}`;

  useEffect(() => {
    const onScroll = () => {
      const el = article.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      const total = r.height - window.innerHeight;
      setProg(total > 0 ? Math.min(100, Math.max(0, Math.round((-r.top / total) * 100))) : 100);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Printing: open every folded evidence box so no quote is lost, and close them again afterwards.
  useEffect(() => {
    const before = () => document.querySelectorAll("details").forEach((d) => { d.dataset.wasOpen = d.open ? "1" : ""; d.open = true; });
    const after = () => document.querySelectorAll("details").forEach((d) => { d.open = d.dataset.wasOpen === "1"; });
    window.addEventListener("beforeprint", before);
    window.addEventListener("afterprint", after);
    return () => {
      window.removeEventListener("beforeprint", before);
      window.removeEventListener("afterprint", after);
    };
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(""), 3500);
    return () => clearTimeout(t);
  }, [toast]);

  const copy = async (text: string, done: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setToast(done);
    } catch {
      setToast("Could not copy. Select the text and copy it by hand.");
    }
  };

  const onMouseUp = () => {
    const s = window.getSelection();
    const text = s ? s.toString().trim() : "";
    const inside = s && s.anchorNode && article.current?.contains(s.anchorNode);
    if (inside && text.length >= 12 && text.length < 400) setSel(text);
  };

  // the most-cited piece of evidence makes the pull quote
  const pull = useMemo(() => {
    const tally = new Map<string, number>();
    report.chapters.forEach((c) => c.cites.forEach((id) => tally.set(id, (tally.get(id) ?? 0) + 1)));
    const best = [...tally.entries()].sort((a, b) => b[1] - a[1])[0];
    const ev = best ? report.evidence[best[0]] : undefined;
    if (!ev || ev.quote.length < 40 || ev.quote.length > 240) return null;
    const at = report.chapters.findIndex((c) => c.cites.includes(ev.id));
    return { ev, at };
  }, [report]);

  const written = report.chapters.filter((c) => c.kind === "ok" && (c.facts ?? 1) > 0).length;
  const gaps = report.chapters.length - written;
  const maxFacts = Math.max(1, ...report.chapters.map((c) => c.facts ?? 0));
  const lc = report.labelCounts;
  const totalLabels = lc.established + lc["single source"] + lc.inference;
  const colClass = cols === 2 ? "md:columns-2 md:gap-11 md:[column-rule:1px_solid_var(--border)]" : "";
  const bodyStyle = { fontSize: size, lineHeight: 1.68 } as const;
  const standfirst = report.goal || report.chapters[0]?.title || "";
  const pdfs = report.sources.filter((s) => s.group === "pdf");
  const webs = report.sources.filter((s) => s.group === "web");
  const others = report.sources.filter((s) => s.group === "other");

  return (
    <div ref={article} onMouseUp={onMouseUp} className="reader-root relative -my-8 ml-[calc(50%-50vw)] w-screen sm:-my-10">
      {/* reading controls */}
      <div className="no-print sticky top-0 z-20 border-b border-border bg-background">
        <div className="mx-auto flex max-w-[1680px] flex-wrap items-center gap-2 px-6 py-2.5">
          <Link href="/reports" className="mr-2 text-sm font-semibold text-accent hover:underline">
            ← All reports
          </Link>
          <span className="text-xs text-muted">{Math.max(1, Math.ceil(minutes * (1 - prog / 100)))} min left</span>
          <div className="flex-1" />
          <button type="button" onClick={() => setSize((s) => Math.max(16, s - 1))} className={chip} aria-label="Smaller text">
            A−
          </button>
          <button type="button" onClick={() => setSize((s) => Math.min(26, s + 1))} className={chip} aria-label="Larger text">
            A+
          </button>
          <button type="button" onClick={() => setCols(1)} className={cols === 1 ? chipOn : chip}>
            1 column
          </button>
          <button type="button" onClick={() => setCols(2)} className={cols === 2 ? chipOn : chip}>
            2 columns
          </button>
          <button type="button" onClick={() => setFaith((v) => !v)} className={faith ? chipOn : chip}>
            Faithfulness
          </button>
          <Link href={goalHref(report.goal || meta.title)} className={chip}>
            Continue researching
          </Link>
          <a href={meta.obsidianUrl} className={chip}>
            Open in Obsidian
          </a>
          <button type="button" onClick={() => window.print()} className={chip}>
            Print
          </button>
        </div>
        <div className="absolute bottom-[-1px] left-0 h-[3px] bg-accent transition-[width]" style={{ width: `${prog}%` }} />
      </div>

      {faith && (
        <div className="no-print border-b border-border bg-surface-hover">
          <div className="mx-auto grid max-w-[1680px] gap-8 px-6 py-5 md:grid-cols-[1fr_1.4fr] md:items-center">
            <div>
              <div className="kicker">Faithfulness of this issue</div>
              <div className="mt-1 font-serif text-3xl leading-tight">
                {totalLabels === 0
                  ? "This issue was written before sentences were labelled."
                  : `${lc.established} of ${totalLabels} labelled claims are established; ${lc.inference} are the writer's own inference and say so.`}
              </div>
              <div className="mt-1 text-sm text-muted">Click a label to see only those sentences in the text.</div>
            </div>
            <div>
              {totalLabels > 0 && (
                <div className="flex h-5 overflow-hidden rounded-[3px]">
                  {(["established", "single source", "inference"] as Label[]).map((k) => (
                    <span
                      key={k}
                      style={{ width: `${(lc[k] / totalLabels) * 100}%` }}
                      className={k === "established" ? "bg-success" : k === "single source" ? "bg-muted" : "bg-warning"}
                    />
                  ))}
                </div>
              )}
              <div className="mt-3 flex flex-wrap gap-2">
                {(["established", "single source", "inference"] as Label[]).map((k) => (
                  <button key={k} type="button" onClick={() => setFocus(focus === k ? "" : k)} className={focus === k ? chipOn : chip}>
                    {lc[k]} {k}
                  </button>
                ))}
                {focus && (
                  <button type="button" onClick={() => setFocus("")} className="text-xs font-semibold text-accent">
                    show all
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* cover */}
      <section className="avoid-break relative overflow-hidden bg-ink text-ink-foreground">
        <div className="absolute inset-y-0 left-0 w-2.5 bg-accent" />
        <div className="mx-auto grid max-w-[1680px] gap-10 px-6 py-12 md:grid-cols-[1.5fr_1fr] md:py-16">
          <div className="flex flex-col">
            <div className="flex flex-wrap gap-x-5 text-xs font-semibold uppercase tracking-[0.14em] text-ink-muted">
              <span className="text-[#ff7a5e]">Deep research</span>
              <span>{meta.date}</span>
            </div>
            <h1 className="mt-8 font-serif text-5xl font-medium leading-[1.02] tracking-tight sm:text-6xl lg:text-7xl">{report.title || meta.title}</h1>
            {standfirst && <p className="mt-6 max-w-2xl font-serif text-xl italic leading-relaxed text-[#c9d4e3] sm:text-2xl">{standfirst}</p>}
            <div className="mt-8 flex flex-wrap gap-x-7 gap-y-1 pt-2 text-sm text-ink-muted">
              <span>
                <b className="text-ink-foreground">{minutes} min</b> read
              </span>
              <span>
                <b className="text-ink-foreground">{meta.words.toLocaleString()}</b> words
              </span>
              <span>
                <b className="text-ink-foreground">{meta.facts}</b> verified facts
              </span>
              <span>
                <b className="text-ink-foreground">{meta.sourcesCount}</b> sources
              </span>
              <span>written locally</span>
            </div>
          </div>
          <CoverArt seed={meta.slug} facts={meta.facts} hero className="hidden h-72 w-full md:block" />
        </div>
      </section>

      {/* in this issue, numbers, figure */}
      <div className="mx-auto max-w-[1680px] px-6 lg:px-14">
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-border py-5">
          <span className="kicker">In this issue</span>
          {report.chapters.map((c) => (
            <a key={c.num} href={`#ch-${c.num}`} className="text-sm font-medium hover:text-accent">
              <b className="font-serif text-xl text-accent">{c.num}</b>&nbsp; {c.title}
            </a>
          ))}
        </div>

        <div className="grid gap-6 py-8 sm:grid-cols-2 lg:grid-cols-4">
          {[
            { n: String(meta.facts), label: "verified facts, each with a quote you can check", color: "border-accent" },
            { n: String(meta.sourcesCount), label: `source${meta.sourcesCount === 1 ? "" : "s"} behind the claims`, color: "border-foreground" },
            { n: String(written), label: `chapter${written === 1 ? "" : "s"} with enough evidence to write`, color: "border-success" },
            { n: String(gaps), label: gaps === 1 ? "honest gap, marked rather than filled" : "honest gaps, marked rather than filled", color: "border-warning" },
          ].map((s) => (
            <div key={s.label} className={`avoid-break border-t-[3px] pt-3 ${s.color}`}>
              <div className="font-serif text-6xl leading-none">{s.n}</div>
              <div className="mt-2 text-sm leading-snug text-muted">{s.label}</div>
            </div>
          ))}
        </div>

        {report.chapters.some((c) => c.facts !== null) && (
          <div className="avoid-break pb-8">
            <div className="kicker text-muted">Fig. 1 — how much evidence stands behind each chapter</div>
            <div className="mt-3 grid grid-cols-[minmax(0,260px)_1fr_110px] items-center gap-x-4 gap-y-2.5 text-sm font-medium">
              {report.chapters.map((c) => {
                const look = statusLook(c);
                return (
                  <div key={c.num} className="contents">
                    <span className="truncate">
                      {c.num}. {c.title}
                    </span>
                    <span className="h-3 rounded-[2px] bg-border">
                      <span
                        className={`block h-3 rounded-[2px] ${look.label === "no evidence" || look.label === "not written" ? "bg-accent" : look.label === "thin" ? "bg-warning" : "bg-success"}`}
                        style={{ width: `${((c.facts ?? 0) / maxFacts) * 100}%` }}
                      />
                    </span>
                    <span className="text-xs font-semibold text-muted">{c.facts === null ? "drawn from the chapters above" : `${c.facts} facts`}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* the lead: executive summary */}
      {report.summary && (
        <section className="border-t border-border">
          <div className="mx-auto max-w-[1680px] px-6 lg:px-14 py-10">
            <div className="kicker">In brief</div>
            <div className={`reader-body drop-cap mt-4 font-serif ${colClass}`} style={bodyStyle}>
              <Body text={report.summary} cite={cite} onCite={(id) => setCite(cite === id ? null : id)} focus={focus} />
            </div>
          </div>
        </section>
      )}

      {/* chapters */}
      {report.chapters.map((c, idx) => {
        const look = statusLook(c);
        return (
          <div key={c.num}>
            <section id={`ch-${c.num}`} className="scroll-mt-20 border-t border-border">
              <div className="mx-auto grid max-w-[1680px] gap-x-8 gap-y-4 px-6 py-10 lg:grid-cols-[80px_minmax(0,1fr)_300px]">
                <div className="font-serif text-6xl leading-none text-accent">{c.num}</div>
                <div>
                  <h2 className="text-4xl leading-tight sm:text-[2.6rem]">{c.title}</h2>
                  <div className="mt-5">
                    {c.kind === "ok" ? (
                      <>
                        <div className={`reader-body font-serif ${colClass}`} style={bodyStyle}>
                          <Body text={c.body} cite={cite} onCite={(id) => setCite(cite === id ? null : id)} focus={focus} />
                        </div>
                        <SentenceFlags desk={desk} section={c.title} />
                      </>
                    ) : (
                      <div className="border border-dashed border-accent bg-accent-soft p-7">
                        <div className="kicker">{c.kind === "gap" ? "A missing page" : "A page the model could not write"}</div>
                        <div className="mt-2 font-serif text-2xl leading-snug">
                          {c.kind === "gap"
                            ? "Your library does not have enough evidence to write this chapter."
                            : "The evidence exists, but the local model failed to write this chapter."}
                        </div>
                        <p className="mt-3 text-[15px] leading-relaxed text-muted">
                          {c.kind === "gap"
                            ? "Rather than guess, the report stops here. Collect sources on this question, then run the goal again."
                            : "The supporting facts are listed in the appendix of the saved note. Free memory and run the goal again."}
                        </p>
                        <Link
                          href={goalHref(`${report.goal || meta.title} — focus on: ${c.title}`)}
                          className="mt-4 inline-block rounded bg-accent px-4 py-2 text-sm font-semibold text-accent-foreground"
                        >
                          {c.kind === "gap" ? "Collect sources for this gap" : "Run it again"}
                        </Link>
                      </div>
                    )}
                  </div>
                </div>
                <aside className="hidden lg:sticky lg:top-16 lg:block lg:max-h-[calc(100vh-5rem)] lg:self-start lg:overflow-y-auto lg:pr-1">
                  <EvidenceNotes chapter={c} report={report} cite={cite} look={look} desk={desk} />
                </aside>
                {/* below 1024 px there is no margin, so the same notes fold open under the chapter instead */}
                <details open={c.cites.includes(cite ?? "")} className="border border-border bg-surface px-4 py-3 lg:hidden">
                  <summary className="cursor-pointer text-sm font-semibold">
                    Evidence behind this chapter{c.cites.length > 0 ? ` · ${c.cites.length} quote${c.cites.length === 1 ? "" : "s"}` : ""}
                    {c.facts !== null ? ` · ${c.facts} facts, ${c.docs ?? 0} documents` : ""}
                  </summary>
                  <div className="mt-3">
                    <EvidenceNotes chapter={c} report={report} cite={cite} look={look} desk={desk} />
                  </div>
                </details>
              </div>
            </section>
            {pull && pull.at === idx && (
              <section className="avoid-break border-y border-border bg-surface-hover">
                <div className="mx-auto grid max-w-[1680px] gap-8 px-6 py-8 md:grid-cols-[80px_1fr]">
                  <div className="font-serif text-[9rem] leading-[0.7] text-accent">&ldquo;</div>
                  <div>
                    <div className="max-w-4xl font-serif text-3xl font-medium italic leading-snug sm:text-4xl">{pull.ev.quote}</div>
                    <div className="mt-4 text-[13px] font-semibold uppercase tracking-widest text-muted">{pull.ev.source}</div>
                  </div>
                </div>
              </section>
            )}
          </div>
        );
      })}

      {/* sources */}
      <section className="border-t-[3px] border-foreground">
        <div className="mx-auto max-w-[1680px] px-6 lg:px-14 py-12">
          <div className="kicker">Further reading</div>
          <h2 className="mb-6 mt-2 text-4xl">Where every claim came from</h2>
          {report.sources.length === 0 ? (
            <p className="font-serif text-xl italic text-muted">This note does not list its sources.</p>
          ) : (
            <div className="grid gap-12 md:grid-cols-2">
              <div className="space-y-8">
                <SourceList title="Papers and PDFs" rows={pdfs} onCopy={copy} />
                <SourceList title="Other" rows={others} onCopy={copy} />
              </div>
              <div className="space-y-4">
                <SourceList title="Web pages" rows={webs} onCopy={copy} />
                <Link href="/knowledge" className="inline-block text-sm font-semibold text-accent hover:underline">
                  See all of this in the knowledge graph →
                </Link>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* colophon */}
      <section className="mx-auto grid max-w-[1680px] gap-10 px-6 pb-16 pt-4 md:grid-cols-3">
        <div>
          <div className="kicker mb-3">How to read the labels</div>
          <div className="space-y-2 text-sm">
            <div>
              <span className={`${tag} ${LABEL_STYLE.established}`}>established</span> cited, from two or more documents
            </div>
            <div>
              <span className={`${tag} ${LABEL_STYLE["single source"]}`}>single source</span> cited, from one document
            </div>
            <div>
              <span className={`${tag} ${LABEL_STYLE.inference}`}>inference</span> not from the sources
            </div>
            <div>
              <span className={`${tag} bg-danger-soft text-danger`}>check figure</span>{" "}
              <span className={`${tag} bg-danger-soft text-danger`}>check subject</span> a number or model name not found in the cited source
            </div>
            {desk.view && (
              <p className="pt-2 text-muted">
                Rate each source in the margin (relevant, not relevant, wrong subject) and flag wrong sentences under each chapter.
                Feedback is saved with this run ({desk.view.engine}).
              </p>
            )}
            {desk.error && <p className="pt-1 text-danger">{desk.error}</p>}
          </div>
        </div>
        <div>
          <div className="kicker mb-3">How it was made</div>
          {report.limitations.length > 0 ? (
            <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-muted">
              {report.limitations.slice(0, 5).map((l) => (
                <li key={l}>{l.replace(/\[|\]\([^)]*\)/g, "")}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm leading-relaxed text-muted">Written by local models on this machine. Verify important conclusions against the quotes.</p>
          )}
        </div>
        <div>
          <div className="kicker mb-3">Was this issue useful?</div>
          {children}
        </div>
      </section>

      {/* highlight menu */}
      {sel && (
        <div role="dialog" aria-label="Highlight actions" className="no-print fixed bottom-6 left-1/2 z-40 w-[min(820px,92%)] -translate-x-1/2 rounded bg-ink p-4 text-ink-foreground shadow-2xl">
          <div className="mb-3 max-h-24 max-w-3xl overflow-auto font-serif text-[17px] italic leading-snug">&ldquo;{sel}&rdquo;</div>
          <div className="flex flex-wrap gap-2 text-[13px] font-semibold">
            <button
              type="button"
              onClick={() => copy(`"${sel}" — ${report.title || meta.title}, The Research Desk, ${meta.date}.`, "Copied as a citation.")}
              className="rounded border border-[#5b7090] px-3 py-2 hover:border-white"
            >
              Copy as citation
            </button>
            <Link href={goalHref(sel)} className="rounded bg-accent px-3 py-2 text-accent-foreground">
              Research this deeper
            </Link>
            <button type="button" onClick={() => setSel("")} className="rounded border border-[#5b7090] px-3 py-2 hover:border-white" aria-label="Close">
              ×
            </button>
          </div>
        </div>
      )}

      {toast && (
        <div role="status" className="no-print fixed bottom-6 right-6 z-50 rounded bg-ink px-4 py-3 text-sm text-ink-foreground shadow-xl">
          {toast}
        </div>
      )}
    </div>
  );
}
