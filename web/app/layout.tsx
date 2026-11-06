import type { Metadata, Viewport } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import Link from "next/link";
import ServerWaker from "@/components/ServerWaker";
import ThemeToggle from "@/components/ThemeToggle";
import "./globals.css";

const jakarta = Plus_Jakarta_Sans({ variable: "--font-jakarta", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Crop Doctor", template: "%s · Crop Doctor" },
  description:
    "An honest crop disease assistant for tomato and potato farmers: it answers when it's sure and asks an expert when it isn't.",
};

export const viewport: Viewport = { themeColor: "#15803d", width: "device-width", initialScale: 1 };

// Runs before the first paint: saved choice, else the phone's setting. Prevents a white flash in dark mode.
const THEME_SCRIPT = `try{var t=localStorage.getItem("cd_theme");if(t!=="light"&&t!=="dark")t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";document.documentElement.dataset.theme=t;if(t==="dark"){var m=document.querySelector('meta[name="theme-color"]');m&&m.setAttribute("content","#0f1411")}}catch(e){}`;

function Logo() {
  return (
    <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden="true">
      <rect width="32" height="32" rx="9" fill="var(--brand)" />
      <path d="M9 22c0-8 5-13 14-13 0 9-5 14-13 14l-1-1Z" fill="#c8f0d6" />
      <path d="M10 22c3-4 6-7 10-9" stroke="var(--brand)" strokeWidth="1.6" fill="none" strokeLinecap="round" />
    </svg>
  );
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${jakarta.variable} h-full antialiased`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="flex min-h-full flex-col">
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-surface focus:px-3 focus:py-2">
          Skip to content
        </a>
        <header className="sticky top-0 z-30 border-b border-border/80 bg-background/85 backdrop-blur">
          <nav className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-3" aria-label="Main">
            <Link href="/" className="flex shrink-0 items-center gap-2 whitespace-nowrap font-bold tracking-tight text-ink">
              <Logo />
              <span className="text-base sm:text-lg">Crop Doctor</span>
            </Link>
            <div className="flex items-center gap-1 whitespace-nowrap text-sm font-semibold">
              <ThemeToggle />
              <Link href="/expert" aria-label="Expert dashboard" title="Expert dashboard"
                className="flex h-10 items-center rounded-full px-2.5 text-ink-2 hover:bg-surface-2 hover:text-ink sm:px-3">
                <span className="text-lg sm:hidden" aria-hidden="true">🧑‍🌾</span>
                <span className="hidden sm:inline">Expert</span>
              </Link>
              <Link href="/check" className="flex h-10 items-center gap-1.5 rounded-full bg-brand px-3.5 text-brand-ink shadow-sm hover:brightness-110 sm:px-4">
                <span aria-hidden="true">📷</span>
                <span className="sm:hidden">Check</span>
                <span className="hidden sm:inline">Check a leaf</span>
              </Link>
            </div>
          </nav>
        </header>
        <ServerWaker />
        <main id="main" className="flex-1">{children}</main>
        <footer className="border-t border-border/80 px-4 py-8 text-sm text-ink-3">
          <div className="mx-auto flex max-w-5xl flex-col gap-2 sm:flex-row sm:justify-between">
            <p>Crop Doctor is a student project. Always confirm with a local agriculture officer or KVK before spraying.</p>
            <p>Treatment notes from TNAU, UC IPM and university extension services.</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
