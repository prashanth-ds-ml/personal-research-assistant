"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { History, PlusCircle, User, Sparkles, ExternalLink, Workflow, Network, Telescope } from "lucide-react";

const NAV_LINKS = [
  { href: "/", label: "History", icon: History },
  { href: "/new", label: "New Research", icon: PlusCircle },
  { href: "/deep", label: "Deep Research", icon: Telescope },
  { href: "/knowledge", label: "Knowledge Graph", icon: Network },
  { href: "/graph", label: "Pipeline Graph", icon: Workflow },
  { href: "/profile", label: "Profile", icon: User },
];

export function SidebarNav() {
  const pathname = usePathname();

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-border px-4 py-8 sm:flex">
      <div className="flex items-center gap-2 px-2">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-accent-foreground">
          <Sparkles className="h-4 w-4" />
        </span>
        <span className="font-semibold tracking-tight">Research Assistant</span>
      </div>

      <nav className="mt-8 flex flex-col gap-1">
        {NAV_LINKS.map((link) => {
          const active = pathname === link.href;
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-accent-soft text-accent"
                  : "text-muted hover:bg-surface-hover hover:text-foreground"
              }`}
            >
              <Icon className="h-4 w-4" />
              {link.label}
            </Link>
          );
        })}
      </nav>

      <a
        href={
          process.env.NEXT_PUBLIC_LANGSMITH_PROJECT_URL ?? "https://smith.langchain.com/"
        }
        target="_blank"
        rel="noopener noreferrer"
        className="mt-auto flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted transition-colors hover:bg-surface-hover hover:text-foreground"
      >
        <ExternalLink className="h-4 w-4" />
        LangSmith traces
      </a>
    </aside>
  );
}
