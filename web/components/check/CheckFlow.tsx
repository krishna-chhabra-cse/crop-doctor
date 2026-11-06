"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError, type CaseView, type Meta } from "@/lib/api";
import { setLanguage, useLanguage, useT } from "@/lib/i18n";
import CaseScreen from "./CaseScreen";
import NewPhoto from "./NewPhoto";

export default function CheckFlow() {
  const params = useSearchParams();
  const router = useRouter();
  const caseId = Number(params.get("case")) || null;
  const [meta, setMeta] = useState<Meta | null>(null);
  const [error, setError] = useState<string | null>(null);
  const language = useLanguage();            // shared with the header switch; also the AI reply language
  const t = useT();
  const [initialCase, setInitialCase] = useState<CaseView | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async (attempt = 0): Promise<void> => {
      try {
        const m = await api.meta();
        if (!cancelled) setMeta(m);
      } catch (e) {
        // The free server may still be waking up: keep trying for about a minute.
        if (!cancelled && attempt < 12) {
          await new Promise((r) => setTimeout(r, 5000));
          return load(attempt + 1);
        }
        if (!cancelled) setError(e instanceof ApiError ? e.message : "Could not load the app.");
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, []);


  const opened = (c: CaseView) => {
    setInitialCase(c);
    const recent = JSON.parse(localStorage.getItem("cd_cases") ?? "[]") as number[];
    localStorage.setItem("cd_cases", JSON.stringify([c.id, ...recent.filter((x) => x !== c.id)].slice(0, 10)));
    router.push(`/check?case=${c.id}`);
  };

  if (error) return <p role="alert" className="rounded-2xl bg-red-soft p-4 text-red">{error}</p>;
  if (!meta)
    return (
      <div className="py-16 text-center text-ink-3" role="status">
        <div className="dot-pulse text-3xl text-brand" aria-hidden="true"><span>●</span> <span>●</span> <span>●</span></div>
        <p className="mt-3">{t("loading")}</p>
      </div>
    );

  if (caseId)
    return (
      <CaseScreen
        key={caseId}
        id={caseId}
        meta={meta}
        language={language}
        initial={initialCase?.id === caseId ? initialCase : null}
        onNew={() => router.push("/check")}
      />
    );

  return (
    <NewPhoto meta={meta} language={language} onLanguage={setLanguage} onOpened={opened}
      showSamples={params.get("sample") === "1"} />
  );
}
