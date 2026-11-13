"use client";

import Link from "next/link";
import { Camera, CircleCheck, CircleHelp, Image as ImageIcon, Leaf, MessageCircle, ScanSearch, UserRound, type LucideIcon } from "lucide-react";
import { useT, type Key } from "@/lib/i18n";
import { REFERENCES } from "@/lib/references";
import { RESULTS as R } from "@/lib/results";

// Round DOWN so a result is never overstated (99.5% shows as 99%, not 100%).
const pct = (x: number) => `${Math.floor(x * 100 + 1e-9)}%`;

// A real field photo (CC BY 4.0, credited on the photo), not a stock or AI image.
const HERO = REFERENCES.potato_late_blight;

const FLOW: { icon: LucideIcon; title: Key; text: Key }[] = [
  { icon: Camera, title: "flow1t", text: "flow1" },
  { icon: ScanSearch, title: "flow2t", text: "flow2" },
  { icon: MessageCircle, title: "flow3t", text: "flow3" },
];

// The three outcomes use the same colours as the result screen: green answer, blue question, violet expert.
const OUTCOMES: { icon: LucideIcon; tone: string; ring: string; title: Key; text: Key }[] = [
  { icon: CircleCheck, tone: "bg-ok-soft text-ok", ring: "var(--ok)", title: "sure", text: "sureT" },
  { icon: CircleHelp, tone: "bg-ask-soft text-ask", ring: "var(--ask)", title: "almost", text: "almostT" },
  { icon: UserRound, tone: "bg-expert-soft text-expert", ring: "var(--expert)", title: "notSure", text: "notSureT" },
];

const card = "rounded-2xl border border-border bg-surface shadow-card";

/* One horizontal bar on a 0-100 axis, with its value and a label. */
function Bar({ label, value, note, strong }: { label: string; value: number; note: string; strong?: boolean }) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-semibold text-ink">{label}</span>
        <span className={`text-4xl font-bold tabular-nums tracking-tight ${strong ? "text-brand" : "text-ink-3"}`}>{pct(value)}</span>
      </div>
      <div className="mt-2 h-3 rounded-full bg-surface-2" aria-hidden="true">
        <div className={`h-3 rounded-full ${strong ? "bg-brand shadow-glow" : "bg-ink-3"}`} style={{ width: pct(value) }} />
      </div>
      <p className="mt-2 text-sm leading-relaxed text-ink-2">{note}</p>
    </div>
  );
}

export default function Home() {
  const t = useT();
  return (
    <div className="mx-auto max-w-5xl px-4">
      {/* ---------- Hero: a real diseased leaf, the promise, one big action ---------- */}
      <section className="rise pt-4 sm:pt-8">
        <div className="relative overflow-hidden rounded-3xl bg-[#0b130e] shadow-card">
          <img src={HERO.src} alt="" className="absolute inset-0 h-full w-full object-cover" fetchPriority="high" />
          <div className="hero-scrim absolute inset-0" aria-hidden="true" />
          <div className="relative px-5 pb-7 pt-28 text-white sm:px-10 sm:pb-10 sm:pt-44">
            <p className="glass inline-flex items-center gap-2 rounded-full px-3 py-1.5 text-sm font-semibold">
              <Leaf className="h-4 w-4 text-[#7ef0ad]" aria-hidden="true" /> {t("heroTag")}
            </p>
            <h1 className="mt-4 max-w-2xl text-[34px] font-bold leading-[1.1] tracking-tight sm:text-5xl sm:leading-[1.08]">
              {t("heroTitle")}
            </h1>
            <p className="mt-4 max-w-xl text-lg leading-relaxed text-white/85">{t("heroText")}</p>
            <div className="mt-7 flex flex-col gap-3 sm:flex-row">
              <Link href="/check"
                className="flex min-h-14 items-center justify-center gap-2 rounded-2xl bg-brand px-7 text-lg font-semibold text-on-brand shadow-glow transition hover:brightness-110">
                <Camera className="h-6 w-6" aria-hidden="true" /> {t("checkNow")}
              </Link>
              <Link href="/check?sample=1"
                className="glass flex min-h-14 items-center justify-center gap-2 rounded-2xl px-6 text-lg font-semibold text-white transition hover:bg-white/20">
                <ImageIcon className="h-5 w-5" aria-hidden="true" /> {t("trySample")}
              </Link>
            </div>
            <p className="mt-6 text-xs text-white/60">{t("heroCredit")}: {HERO.credit}</p>
          </div>
        </div>

        {/* Only numbers the project has measured. */}
        <dl className="rise-2 mt-4 grid grid-cols-3 gap-3">
          {[
            { v: pct(R.finalFieldAccuracy), l: t("statAccuracy") },
            { v: "8", l: t("statLanguages") },
            { v: t("free"), l: t("statFree") },
          ].map((s) => (
            <div key={s.l} className={`${card} px-3 py-4 text-center sm:px-5`}>
              <dt className="sr-only">{s.l}</dt>
              <dd className="text-2xl font-bold tracking-tight text-brand sm:text-3xl">{s.v}</dd>
              <dd className="mt-1 text-xs leading-snug text-ink-2 sm:text-sm">{s.l}</dd>
            </div>
          ))}
        </dl>
      </section>

      {/* ---------- How it works ---------- */}
      <section aria-labelledby="how" className="pt-14">
        <h2 id="how" className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">{t("howItWorks")}</h2>
        <ol className="mt-5 grid gap-4 sm:grid-cols-3">
          {FLOW.map((f, i) => (
            <li key={f.title} className={`${card} p-5`}>
              <div className="flex items-center justify-between">
                <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-ok-soft text-ok" aria-hidden="true">
                  <f.icon className="h-6 w-6" />
                </span>
                <span className="text-4xl font-bold text-surface-2" aria-hidden="true">0{i + 1}</span>
              </div>
              <h3 className="mt-4 text-lg font-semibold text-ink"><span className="sr-only">{t("step")} {i + 1}: </span>{t(f.title)}</h3>
              <p className="mt-1 leading-relaxed text-ink-2">{t(f.text)}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* ---------- Three kinds of answer ---------- */}
      <section aria-labelledby="answers" className="pt-14">
        <h2 id="answers" className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">{t("kinds")}</h2>
        <p className="mt-2 max-w-2xl leading-relaxed text-ink-2">{t("kindsSub")}</p>
        <ul className="mt-5 grid gap-4 sm:grid-cols-3">
          {OUTCOMES.map((o) => (
            <li key={o.title} className={`${card} border-t-4 p-5`} style={{ borderTopColor: o.ring }}>
              <span className={`flex h-12 w-12 items-center justify-center rounded-full ${o.tone}`} aria-hidden="true">
                <o.icon className="h-6 w-6" />
              </span>
              <h3 className="mt-4 text-lg font-semibold text-ink">{t(o.title)}</h3>
              <p className="mt-1 leading-relaxed text-ink-2">{t(o.text)}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* ---------- Why honesty matters: the measured results ---------- */}
      <section aria-labelledby="why" className="pb-16 pt-14">
        <h2 id="why" className="text-2xl font-bold tracking-tight text-ink sm:text-3xl">{t("whyTitle")}</h2>
        <p className="mt-2 leading-relaxed text-ink-2">{t("whyTested", { n: R.fieldTestPhotos.toLocaleString("en-IN") })}</p>

        <div className={`${card} mt-5 space-y-7 p-5 sm:p-8`}>
          <Bar label={`${t("whyUsualTag")}: ${t("whyFieldLabel")}`} value={R.labOnlyFieldAccuracy}
            note={t("whyFieldNote", { lab: pct(R.labAccuracy), field: pct(R.labOnlyFieldAccuracy), conf: pct(R.labOnlyFieldConfidence) })} />
          <Bar strong label={`${t("whyOursTag")}: ${t("whyFirstLabel")}`} value={R.finalFieldAccuracy}
            note={t("whyFirstNote", { tz: pct(R.tanzaniaAccuracy), pd: pct(R.plantdocAccuracy) })} />

          <dl className="grid gap-6 border-t border-border pt-6 sm:grid-cols-2">
            <div>
              <dt className="font-semibold text-ink">{t("whyCoverLabel")}</dt>
              <dd className="mt-1">
                <span className="text-4xl font-bold tabular-nums tracking-tight text-brand">{pct(R.coverage)}</span>
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
                <span className="text-4xl font-bold tabular-nums tracking-tight text-brand">{pct(R.accuracyWhenAnswered)}</span>
                <span className="mt-2 block text-sm leading-relaxed text-ink-2">{t("whyAloneNote", { answered: pct(R.answeredByAssistant) })}</span>
              </dd>
            </div>
          </dl>
        </div>
      </section>
    </div>
  );
}
