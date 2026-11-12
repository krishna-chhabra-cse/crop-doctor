"use client";

import Link from "next/link";
import { useT } from "@/lib/i18n";
import { useRecentCases } from "@/lib/recent";

export default function RecentChecks() {
  const ids = useRecentCases();
  const t = useT();
  if (!ids.length) return null;
  return (
    <section aria-labelledby="recent" className="border-t border-border pt-5">
      <h2 id="recent" className="text-lg font-semibold text-ink">{t("recentChecks")}</h2>
      <ul className="mt-3 flex flex-wrap gap-2">
        {ids.map((id) => (
          <li key={id}>
            <Link href={`/check?case=${id}`}
              className="flex min-h-12 items-center rounded-xl border border-border bg-surface px-4 font-semibold text-ink hover:bg-surface-2">
              {t("checkNo")} #{id}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
