"use client";

import Link from "next/link";
import { Camera, Check, CircleCheck, CircleHelp, Image as ImageIcon, MessageCircle, ScanSearch, UserRound, type LucideIcon } from "lucide-react";
import { useT, type Key } from "@/lib/i18n";
import { RESULTS as R } from "@/lib/results";

// Round DOWN so a result is never overstated (99.5% shows as 99%, not 100%).
const pct = (x: number) => `${Math.floor(x * 100 + 1e-9)}%`;

const FLOW: { icon: LucideIcon; title: Key; text: Key }[] = [
  { icon: Camera, title: "flow1t", text: "flow1" },
  { icon: ScanSearch, title: "flow2t", text: "flow2" },
  { icon: MessageCircle, title: "flow3t", text: "flow3" },
];

// The three outcomes use the same colours as the result screen: green answer, blue question, violet expert.
const OUTCOMES: { icon: LucideIcon; tone: string; title: Key; text: Key }[] = [
  { icon: CircleCheck, tone: "bg-ok-soft text-ok", title: "sure", text: "sureT" },
  { icon: CircleHelp, tone: "bg-ask-soft text-ask", title: "almost", text: "almostT" },
  { icon: UserRound, tone: "bg-expert-soft text-expert", title: "notSure", text: "notSureT" },
];

/* One horizontal bar on a 0-100 axis, with its value and a label. */
function Bar({ label, value, note, strong }: { label: string; value: number; note: string; strong?: boolean }) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-semibold text-ink">{label}</span>
        <span className={`text-3xl font-bold tabular-nums ${strong ? "text-brand" : "text-ink-2"}`}>{pct(value)}</span>
      </div>
      <div className="mt-2 h-3 rounded-full bg-surface-2" aria-hidden="true">
        <div className={`h-3 rounded-full ${strong ? "bg-brand" : "bg-ink-3"}`} style={{ width: pct(value) }} />
      </div>
      <p className="mt-2 text-sm leading-relaxed text-ink-2">{note}</p>
    </div>
  );
}

export default function Home() {
  const t = useT();
  return (
    <div className="mx-auto max-w-3xl px-4">
      <section className="pb-10 pt-8 sm:pt-14">
        <p className="text-sm font-semibold text-ok">{t("heroTag")}</p>
        <h1 className="mt-2 text-[28px] font-bold leading-[34px] text-ink sm:text-4xl sm:leading-[42px]">
          {t("heroTitle")}
        </h1>
        <p className="mt-3 max-w-xl text-lg leading-7 text-ink-2">{t("heroText")}</p>
        <div className="mt-6 flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-4">
          <Link href="/check" className="flex min-h-14 items-center justify-center gap-2 rounded-xl bg-brand px-6 text-lg font-semibold text-on-brand hover:opacity-90">
            <Camera className="h-6 w-6" aria-hidden="true" /> {t("checkNow")}
          </Link>
          <Link href="/check?sample=1" className="flex min-h-12 items-center justify-center gap-2 rounded-xl px-4 font-semibold text-ink-2 underline underline-offset-4 hover:text-ink">
            <ImageIcon className="h-5 w-5" aria-hidden="true" /> {t("trySample")}
          </Link>
        </div>
        <ul className="mt-5 flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink-2">
          {(["free", "noInstall", "languages8"] as const).map((k) => (
            <li key={k} className="flex items-center gap-1.5"><Check className="h-4 w-4 text-ok" aria-hidden="true" />{t(k)}</li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="how" className="pb-10">
        <h2 id="how" className="text-[22px] font-bold leading-7 text-ink">{t("howItWorks")}</h2>
        <ol className="mt-3 divide-y divide-border border-y border-border">
          {FLOW.map((f, i) => (
            <li key={f.title} className="flex gap-4 py-4">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-surface-2 text-ink" aria-hidden="true">
                <f.icon className="h-6 w-6" />
              </span>
              <div>
                <h3 className="text-lg font-semibold text-ink"><span className="text-ink-3">{i + 1}.</span> {t(f.title)}</h3>
                <p className="mt-0.5 leading-relaxed text-ink-2">{t(f.text)}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="answers" className="pb-10">
        <h2 id="answers" className="text-[22px] font-bold leading-7 text-ink">{t("kinds")}</h2>
        <p className="mt-1 leading-relaxed text-ink-2">{t("kindsSub")}</p>
        <ul className="mt-3 divide-y divide-border border-y border-border">
          {OUTCOMES.map((o) => (
            <li key={o.title} className="flex gap-4 py-4">
              <span className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full ${o.tone}`} aria-hidden="true">
                <o.icon className="h-6 w-6" />
              </span>
              <div>
                <h3 className="text-lg font-semibold text-ink">{t(o.title)}</h3>
                <p className="mt-0.5 leading-relaxed text-ink-2">{t(o.text)}</p>
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="why" className="pb-14">
        <h2 id="why" className="text-[22px] font-bold leading-7 text-ink">{t("whyTitle")}</h2>
        <p className="mt-1 leading-relaxed text-ink-2">{t("whyTested", { n: R.fieldTestPhotos.toLocaleString("en-IN") })}</p>

        <div className="mt-4 space-y-6 rounded-xl border border-border bg-surface p-4 sm:p-6">
          <Bar label={`${t("whyUsualTag")}: ${t("whyFieldLabel")}`} value={R.labOnlyFieldAccuracy}
            note={t("whyFieldNote", { lab: pct(R.labAccuracy), field: pct(R.labOnlyFieldAccuracy), conf: pct(R.labOnlyFieldConfidence) })} />
          <Bar strong label={`${t("whyOursTag")}: ${t("whyFirstLabel")}`} value={R.finalFieldAccuracy}
            note={t("whyFirstNote", { tz: pct(R.tanzaniaAccuracy), pd: pct(R.plantdocAccuracy) })} />

          <dl className="grid gap-5 border-t border-border pt-5 sm:grid-cols-2">
            <div>
              <dt className="font-semibold text-ink">{t("whyCoverLabel")}</dt>
              <dd className="mt-1">
                <span className="text-3xl font-bold tabular-nums text-brand">{pct(R.coverage)}</span>
                <span className="relative mt-2 block h-2 rounded-full bg-surface-2" aria-hidden="true">
                  <span className="block h-2 rounded-full bg-brand" style={{ width: pct(R.coverage) }} />
                  <span className="absolute -top-1 h-4 w-0.5 bg-ink" style={{ left: pct(R.coverageTarget) }} title={t("whyTarget", { p: pct(R.coverageTarget) })} />
                </span>
                <span className="mt-2 block text-sm leading-relaxed text-ink-2">{t("whyCoverNote", { target: pct(R.coverageTarget) })}</span>
              </dd>
            </div>
            <div>
              <dt className="font-semibold text-ink">{t("whyAloneLabel")}</dt>
              <dd className="mt-1">
                <span className="text-3xl font-bold tabular-nums text-brand">{pct(R.accuracyWhenAnswered)}</span>
                <span className="mt-2 block text-sm leading-relaxed text-ink-2">{t("whyAloneNote", { answered: pct(R.answeredByAssistant) })}</span>
              </dd>
            </div>
          </dl>
        </div>
      </section>
    </div>
  );
}
