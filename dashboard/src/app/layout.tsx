import type { Metadata } from "next";
import "./globals.css";
import { Masthead } from "@/components/masthead";
import { ToastProvider } from "@/components/toast";

export const metadata: Metadata = {
  title: "The Research Desk",
  description: "Personal, fully-local research assistant",
};

// Runs before the page paints so a remembered theme never flashes the other one.
const THEME_BOOT = `try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT }} />
      </head>
      <body className="min-h-full bg-background font-sans text-foreground">
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded focus:bg-accent focus:px-4 focus:py-2 focus:text-accent-foreground">
          Skip to the content
        </a>
        <ToastProvider>
          <Masthead />
          <main id="main" className="mx-auto w-full max-w-[1680px] px-6 py-8 sm:py-10 lg:px-14">
            {children}
          </main>
        </ToastProvider>
      </body>
    </html>
  );
}
