import type { Metadata, Viewport } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import Link from "next/link";
import ServerWaker from "@/components/ServerWaker";
import "./globals.css";

const jakarta = Plus_Jakarta_Sans({ variable: "--font-jakarta", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Crop Doctor", template: "%s · Crop Doctor" },
  description:
    "An honest crop disease assistant for tomato and potato farmers: it answers when it's sure and asks an expert when it isn't.",
};

export const viewport: Viewport = { themeColor: "#15803d", width: "device-width", initialScale: 1 };

function Logo() {
  return (
    <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden="true">
      <rect width="32" height="32" rx="9" fill="#15803d" />
      <path d="M9 22c0-8 5-13 14-13 0 9-5 14-13 14l-1-1Z" fill="#c8f0d6" />
      <path d="M10 22c3-4 6-7 10-9" stroke="#15803d" strokeWidth="1.6" fill="none" strokeLinecap="round" />
    </svg>
  );
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${jakarta.variable} h-full antialiased`}>
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
              <Link href="/expert" className="rounded-full px-2.5 py-2 text-ink-2 hover:bg-surface-2 hover:text-ink sm:px-3">
                Expert
              </Link>
              <Link href="/check" className="rounded-full bg-brand px-3.5 py-2 text-brand-ink shadow-sm hover:brightness-110 sm:px-4">
                Check a leaf
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
