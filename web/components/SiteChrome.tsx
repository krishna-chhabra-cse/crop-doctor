"use client";

import Link from "next/link";
import { setLanguage, useLanguage, useT } from "@/lib/i18n";
import ThemeToggle from "./ThemeToggle";

function LanguageToggle() {
  const language = useLanguage();
  const hindi = language === "Hindi";
  return (
    <button
      type="button"
      onClick={() => setLanguage(hindi ? "English" : "Hindi")}
      aria-label={hindi ? "Switch to English" : "हिन्दी में बदलें"}
      title={hindi ? "English" : "हिन्दी"}
      className="flex h-10 min-w-10 items-center justify-center rounded-full border border-border px-2.5 text-sm font-bold text-ink hover:bg-surface-2"
    >
      {hindi ? "EN" : "हिं"}
    </button>
  );
}

export function SiteNav() {
  const t = useT();
  return (
    <div className="flex items-center gap-1 whitespace-nowrap text-sm font-semibold">
      <LanguageToggle />
      <ThemeToggle />
      <Link href="/expert" aria-label={t("expert")} title={t("expert")}
        className="flex h-10 items-center rounded-full px-2.5 text-ink-2 hover:bg-surface-2 hover:text-ink sm:px-3">
        <span className="text-lg sm:hidden" aria-hidden="true">🧑‍🌾</span>
        <span className="hidden sm:inline">{t("expert")}</span>
      </Link>
      <Link href="/check" className="flex h-10 items-center gap-1.5 rounded-full bg-brand px-3.5 text-brand-ink shadow-sm hover:brightness-110 sm:px-4">
        <span aria-hidden="true">📷</span>
        <span className="sm:hidden">{t("check")}</span>
        <span className="hidden sm:inline">{t("checkLeaf")}</span>
      </Link>
    </div>
  );
}

export function SiteFooter() {
  const t = useT();
  return (
    <footer className="border-t border-border/80 px-4 py-8 text-sm text-ink-3">
      <div className="mx-auto flex max-w-5xl flex-col gap-2 sm:flex-row sm:justify-between">
        <p>{t("footerNote")}</p>
        <p>{t("footerSources")}</p>
      </div>
    </footer>
  );
}
