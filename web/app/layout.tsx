import type { Metadata, Viewport } from "next";
import { Noto_Sans, Noto_Sans_Devanagari } from "next/font/google";
import Link from "next/link";
import ServerWaker from "@/components/ServerWaker";
import { SiteFooter, SiteNav } from "@/components/SiteChrome";
import "./globals.css";

// One type family for both scripts, so mixed lines ("KVK से पुष्टि करें") match. Both are variable fonts.
// Devanagari is not preloaded: its unicode-range means English-only visitors never download it.
const noto = Noto_Sans({ variable: "--font-noto", subsets: ["latin"], display: "swap" });
const notoDeva = Noto_Sans_Devanagari({ variable: "--font-noto-deva", subsets: ["devanagari"], display: "swap", preload: false });

export const metadata: Metadata = {
  title: { default: "Crop Doctor", template: "%s · Crop Doctor" },
  description:
    "An honest crop disease assistant for tomato and potato farmers: it answers when it's sure and asks an expert when it isn't.",
};

export const viewport: Viewport = { themeColor: "#f6f7f4", width: "device-width", initialScale: 1 };

// Runs before the first paint: saved choice, else the phone's setting. Prevents a white flash in dark mode.
const THEME_SCRIPT = `try{var t=localStorage.getItem("cd_theme");if(t!=="light"&&t!=="dark")t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";document.documentElement.dataset.theme=t;if(localStorage.getItem("cd_language")==="Hindi")document.documentElement.lang="hi";if(t==="dark"){var m=document.querySelector('meta[name="theme-color"]');m&&m.setAttribute("content","#0e1311")}}catch(e){}`;

function Logo() {
  return (
    <svg viewBox="0 0 32 32" className="h-8 w-8" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--brand)" />
      <path d="M9 22c0-8 5-13 14-13 0 9-5 14-13 14l-1-1Z" fill="var(--on-brand)" />
      <path d="M10 22c3-4 6-7 10-9" stroke="var(--brand)" strokeWidth="1.6" fill="none" strokeLinecap="round" />
    </svg>
  );
}

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${noto.variable} ${notoDeva.variable} h-full antialiased`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body className="flex min-h-full flex-col">
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-xl focus:bg-surface focus:px-3 focus:py-2">
          Skip to content
        </a>
        <header className="sticky top-0 z-30 border-b border-border bg-background/90 backdrop-blur">
          <nav className="mx-auto flex max-w-5xl items-center justify-between gap-3 px-4 py-2" aria-label="Main">
            <Link href="/" className="flex min-h-12 shrink-0 items-center gap-2 whitespace-nowrap text-lg font-bold text-ink">
              <Logo />
              <span>Crop Doctor</span>
            </Link>
            <SiteNav />
          </nav>
        </header>
        <ServerWaker />
        <main id="main" className="flex-1">{children}</main>
        <SiteFooter />
      </body>
    </html>
  );
}
