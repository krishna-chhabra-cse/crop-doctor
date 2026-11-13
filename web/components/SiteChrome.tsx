"use client";

import Link from "next/link";
import { ChevronDown, Languages } from "lucide-react";
import { NATIVE, setLanguage, useLanguage, useT } from "@/lib/i18n";
import ThemeToggle from "./ThemeToggle";

// One setting drives the screen text and the AI reply language, so the header offers all of them (the same list as
// step 3 of a check). A plain toggle between English and Hindi silently replaced a farmer's Tamil, Telugu...
function LanguagePicker() {
  const language = useLanguage();
  return (
    <label className="relative flex h-12 items-center rounded-xl border border-border text-ink hover:bg-surface-2">
      <Languages className="pointer-events-none absolute left-3 h-5 w-5 text-ink-2" aria-hidden="true" />
      <span className="sr-only">Language / भाषा</span>
      <select
        value={NATIVE[language] ? language : "English"}
        onChange={(e) => setLanguage(e.target.value)}
        className="h-full cursor-pointer appearance-none rounded-xl bg-transparent pl-10 pr-8 font-semibold text-ink"
      >
        {Object.entries(NATIVE).map(([value, name]) => (
          <option key={value} value={value} className="bg-surface text-ink">{name}</option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2.5 h-4 w-4 text-ink-3" aria-hidden="true" />
    </label>
  );
}

export function SiteNav() {
  return (
    <div className="flex items-center gap-1">
      <LanguagePicker />
      <ThemeToggle />
    </div>
  );
}

export function SiteFooter() {
  const t = useT();
  return (
    <footer className="border-t border-border px-4 py-8 text-sm text-ink-3">
      <div className="mx-auto flex max-w-5xl flex-col gap-2 sm:flex-row sm:justify-between">
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
