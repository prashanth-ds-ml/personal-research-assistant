"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Search } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";
import { MemoryChip } from "@/components/memory-chip";
import { RunChip } from "@/components/run-chip";
import { CommandPalette } from "@/components/command-palette";

const MAIN = [
  { href: "/", label: "Front page" },
  { href: "/deep", label: "Research" },
  { href: "/runs", label: "Runs" },
  { href: "/reports", label: "Reports" },
  { href: "/library", label: "Library" },
  { href: "/knowledge", label: "Graph" },
];

const MORE = [
  { href: "/compare", label: "Compare issues", sub: "what changed between runs" },
  { href: "/graph", label: "Pipeline graph", sub: "how a run flows" },
  { href: "/new", label: "Quick research", sub: "a short note in minutes" },
  { href: "/profile", label: "Profile", sub: "what it has learned" },
  { href: "/settings", label: "Settings", sub: "models, sources, quality" },
];

function isActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  if (href === "/reports") return pathname.startsWith("/reports") || pathname.startsWith("/research");
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function Masthead() {
  const pathname = usePathname();
  const [more, setMore] = useState(false);
  const [palette, setPalette] = useState(false);

  return (
    <header className="no-print relative border-b-2 border-foreground">
      <div className="mx-auto flex max-w-[1680px] flex-wrap items-end gap-x-6 gap-y-2 px-6 lg:px-14 pt-5 pb-3">
        <Link href="/" className="font-serif text-2xl font-semibold leading-none tracking-tight sm:text-3xl">
          The Research Desk
        </Link>
        <MemoryChip />
        <RunChip />
        <div className="flex-1" />
        <button
          type="button"
          aria-label="Search everything"
          onClick={() => setPalette(true)}
          className="flex items-center gap-2 rounded border border-border bg-surface px-3 py-1.5 text-xs font-semibold hover:border-accent"
        >
          <Search className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Search everything</span>
          <kbd className="hidden text-muted sm:inline">Ctrl K</kbd>
        </button>
        <ThemeToggle />
      </div>
      <nav aria-label="Main" className="mx-auto flex max-w-[1680px] flex-wrap gap-x-6 gap-y-1 px-6 lg:px-14">
        {MAIN.map((l) => {
          const active = isActive(pathname, l.href);
          return (
            <Link
              key={l.href}
              href={l.href}
              aria-current={active ? "page" : undefined}
              className={`-mb-[2px] border-b-2 pb-2 text-sm font-medium transition-colors ${
                active ? "border-accent text-accent" : "border-transparent text-muted hover:text-foreground"
              }`}
            >
              {l.label}
            </Link>
          );
        })}
        <div className="relative">
          <button
            type="button"
            onClick={() => setMore((v) => !v)}
            aria-expanded={more}
            className="-mb-[2px] block border-b-2 border-transparent pb-2 text-sm font-medium leading-normal text-muted hover:text-foreground"
          >
            More ▾
          </button>
          {more && (
            <div className="absolute left-0 top-full z-30 mt-1 w-64 rounded border border-border bg-surface p-2 shadow-xl">
              {MORE.map((m) => (
                <Link
                  key={m.href}
                  href={m.href}
                  onClick={() => setMore(false)}
                  className="block rounded px-3 py-2 text-sm font-medium hover:bg-surface-hover"
                >
                  {m.label}
                  <span className="block text-xs font-normal text-muted">{m.sub}</span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </nav>
      <CommandPalette open={palette} onOpenChange={setPalette} />
    </header>
  );
}
