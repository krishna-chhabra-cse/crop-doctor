"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { LoaderCircle } from "lucide-react";
import { api, errorKey, type CaseView, type Meta } from "@/lib/api";
import { setLanguage, useLanguage, useT, type Key } from "@/lib/i18n";
import { rememberCase } from "@/lib/recent";
import CaseScreen from "./CaseScreen";
import NewPhoto from "./NewPhoto";
import RecentChecks from "./RecentChecks";

/** Suspense fallback for the check page (translated once the browser has the saved language). */
export function CheckLoading() {
  const t = useT();
  return <p className="py-10 text-center text-ink-3">{t("loadingCase")}</p>;
}

export default function CheckFlow() {
  const params = useSearchParams();
  const router = useRouter();
  const caseId = Number(params.get("case")) || null;
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState<Key | null>(null);
  const [attempt, setAttempt] = useState(0);   // bumped by "Try again"
  const language = useLanguage();            // shared with the header switch; also the AI reply language
  const [initialCase, setInitialCase] = useState<CaseView | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async (n = 0): Promise<void> => {
      try {
        const m = await api.meta();
        if (!cancelled) setMeta(m);
      } catch (e) {
        // The free server may still be starting: keep trying for about a minute (not when offline).
        const offline = typeof navigator !== "undefined" && navigator.onLine === false;
        if (!cancelled && n < 12 && !offline) {
          await new Promise((r) => setTimeout(r, 5000));
          return load(n + 1);
        }
        if (!cancelled) setError(errorKey(e));
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const opened = (c: CaseView) => {
    setInitialCase(c);
    rememberCase(c.id);
    router.push(`/check?case=${c.id}`);
  };

  if (caseId)
    return meta ? (
      <CaseScreen
        key={caseId}
        id={caseId}
        meta={meta}
        language={language}
        initial={initialCase?.id === caseId ? initialCase : null}
        onNew={() => router.push("/check")}
      />
    ) : (
      <Waiting error={error} onRetry={() => { setError(null); setAttempt((a) => a + 1); }} />
    );

  return (
    <div className="space-y-5">
      {meta ? (
        <NewPhoto meta={meta} language={language} onLanguage={setLanguage} onOpened={opened}
          showSamples={params.get("sample") === "1"} />
      ) : (
        <Waiting error={error} onRetry={() => { setError(null); setAttempt((a) => a + 1); }} />
      )}
      <RecentChecks />
    </div>
  );
}

/** While the app data loads (the server may be starting), or a translated error with Try again. */
function Waiting({ error, onRetry }: { error: Key | null; onRetry: () => void }) {
  const t = useT();
  if (error)
    return (
      <div role="alert" className="rounded-xl bg-urgent-soft p-4 text-urgent">
        <p>{t(error)}</p>
        <button type="button" onClick={onRetry}
          className="mt-3 min-h-12 rounded-xl bg-brand px-5 font-semibold text-on-brand">{t("retry")}</button>
      </div>
    );
  return (
    <div className="py-16 text-center text-ink-3" role="status">
      <LoaderCircle className="spin mx-auto h-8 w-8 text-brand" aria-hidden="true" />
      <p className="mt-3">{t("loading")}</p>
    </div>
  );
}
