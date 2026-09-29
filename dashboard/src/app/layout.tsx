import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { SidebarNav } from "@/components/sidebar-nav";
import { MobileNav } from "@/components/mobile-nav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Research Assistant",
  description: "Personal, fully-local research assistant dashboard",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
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
