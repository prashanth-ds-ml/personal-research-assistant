import type { Metadata } from "next";
import "./globals.css";
import { SidebarNav } from "@/components/sidebar-nav";
import { MobileNav } from "@/components/mobile-nav";

export const metadata: Metadata = {
  title: "Research Assistant",
  description: "Personal, fully-local research assistant dashboard",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className="h-full antialiased"
    >
      <body className="min-h-full bg-background text-foreground">
        <MobileNav />
        <div className="mx-auto flex w-full max-w-7xl sm:min-h-screen">
          <SidebarNav />
          <main className="min-w-0 flex-1 px-6 py-8 sm:px-10 sm:py-10">
            <div className="mx-auto w-full max-w-3xl">{children}</div>
          </main>
        </div>
      </body>
    </html>
  );
}
