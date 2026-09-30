"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { History, PlusCircle, User, Sparkles, Telescope } from "lucide-react";

const NAV_LINKS = [
  { href: "/", label: "History", icon: History },
  { href: "/new", label: "New", icon: PlusCircle },
  { href: "/deep", label: "Deep", icon: Telescope },
  { href: "/profile", label: "Profile", icon: User },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <header className="flex items-center justify-between border-b border-border px-4 py-3 sm:hidden">
      <div className="flex items-center gap-2">
        <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-accent text-accent-foreground">
          <Sparkles className="h-3.5 w-3.5" />
        </span>
        <span className="text-sm font-semibold">Research Assistant</span>
      </div>
      <nav className="flex gap-1">
        {NAV_LINKS.map((link) => {
          const active = pathname === link.href;
          const Icon = link.icon;
          return (
            <Link
              key={link.href}
              href={link.href}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium ${
                active ? "bg-accent-soft text-accent" : "text-muted"
              }`}
            >
              <Icon className="h-3.5 w-3.5" />
              {link.label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
