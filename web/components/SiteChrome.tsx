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
      lang={hindi ? "en" : "hi"}
      className="flex h-12 min-w-12 items-center justify-center rounded-xl border border-border px-3 font-semibold text-ink hover:bg-surface-2"
    >
      {hindi ? "English" : "हिन्दी"}
    </button>
  );
}

export function SiteNav() {
  return (
    <div className="flex items-center gap-1">
      <LanguageToggle />
      <ThemeToggle />
    </div>
  );
}

export function SiteFooter() {
  const t = useT();
  return (
    <footer className="bg-surface-2 px-5 py-12 text-ink-2 sm:px-8">
      <div className="mx-auto flex max-w-[1280px] flex-col gap-3 sm:flex-row sm:justify-between">
        <div className="space-y-2">
          <p>{t("footerNote")}</p>
          <p>{t("footerSources")}</p>
        </div>
        <Link href="/expert" className="flex min-h-12 items-center self-start font-semibold text-ink-2 underline underline-offset-4 hover:text-ink">
          {t("expertLink")}
        </Link>
      </div>
    </footer>
  );
}
