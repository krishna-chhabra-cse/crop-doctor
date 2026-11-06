"use client";

import Link from "next/link";
import { useT, type Key } from "@/lib/i18n";
import { RESULTS as R } from "@/lib/results";

const pct = (x: number) => `${Math.round(x * 100)}%`;

function Stat({ value, label, note, tone = "brand" }: { value: string; label: string; note: string; tone?: "brand" | "red" }) {
  return (
    <div className="rounded-3xl border border-border bg-surface p-5 shadow-card">
      <div className={`text-4xl font-extrabold tracking-tight ${tone === "red" ? "text-red" : "text-brand"}`}>{value}</div>
      <div className="mt-1 font-semibold text-ink">{label}</div>
      <p className="mt-1 text-sm text-ink-3">{note}</p>
    </div>
  );
}

/* A small phone showing what a result looks like: the picture explains the app before any reading. */
function PhonePreview() {
  return (
    <div className="relative mx-auto w-[270px] rounded-[2.5rem] border-[10px] border-ink/90 bg-background p-3 shadow-card" aria-hidden="true">
      <div className="mx-auto mb-3 h-1.5 w-16 rounded-full bg-ink/20" />
      <div className="space-y-3 rounded-3xl border border-border bg-surface p-3">
        <div className="flex items-center gap-3">
          <div className="relative flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-soft text-4xl">
            🍃
            <span className="absolute -bottom-1.5 -right-1.5 flex h-7 w-7 items-center justify-center rounded-full border-2 border-surface bg-red-soft text-sm">🚨</span>
          </div>
          <div>
            <p className="text-[10px] font-semibold uppercase text-ink-3">Most likely</p>
            <p className="text-sm font-extrabold leading-tight text-ink">Tomato late blight</p>
            <div className="mt-1 flex gap-0.5">
              {Array.from({ length: 10 }, (_, i) => <span key={i} className={`h-1.5 w-1.5 rounded-full ${i < 9 ? "bg-brand" : "bg-surface-2"}`} />)}
            </div>
          </div>
        </div>
        <div className="rounded-xl bg-red-soft p-2">
          <p className="text-xs font-extrabold text-red">⏰ Act within 24 hours</p>
          <div className="mt-1.5 grid grid-cols-3 gap-1 text-[9px] font-bold">
            <span className="rounded bg-surface/70 py-0.5 text-center text-ink-3">🟢 Wait</span>
            <span className="rounded bg-surface/70 py-0.5 text-center text-ink-3">🟠 Week</span>
            <span className="rounded bg-red py-0.5 text-center text-background">🔴 Today</span>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-1.5 text-center text-[9px] font-semibold text-ink">
          {[["✂️", "Remove leaves"], ["📢", "Tell neighbours"], ["🧑‍🌾", "Ask KVK"]].map(([i, t]) => (
            <div key={t} className="rounded-lg border border-border p-1.5"><div className="text-lg">{i}</div>{t}</div>
          ))}
        </div>
        <div className="flex items-center gap-1.5 rounded-xl bg-surface-2 px-2 py-1.5 text-[10px] font-bold text-ink">🔊 Listen in हिन्दी</div>
      </div>
    </div>
  );
}

const FLOW: { icon: string; title: Key; text: Key }[] = [
  { icon: "📷", title: "flow1t", text: "flow1" },
  { icon: "🔎", title: "flow2t", text: "flow2" },
  { icon: "💬", title: "flow3t", text: "flow3" },
];

const OUTCOMES: { icon: string; tone: string; title: Key; text: Key }[] = [
  { icon: "✅", tone: "bg-brand-soft text-brand", title: "sure", text: "sureT" },
  { icon: "❓", tone: "bg-blue-soft text-blue", title: "almost", text: "almostT" },
  { icon: "🧑‍🌾", tone: "bg-amber-soft text-amber", title: "notSure", text: "notSureT" },
];

export default function Home() {
  const t = useT();
  return (
    <div className="mx-auto max-w-5xl px-4">
      <section className="grid items-center gap-10 pb-14 pt-10 sm:pt-16 md:grid-cols-[1.2fr_1fr]">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full bg-brand-soft px-3 py-1 text-sm font-semibold text-brand">
            <span aria-hidden="true">🍅 🥔</span> {t("heroTag")}
          </p>
          <h1 className="mt-4 text-4xl font-extrabold leading-[1.08] tracking-tight text-ink sm:text-6xl">
            {t("heroTitle")}
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-ink-2">
            {t("heroText")}
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link href="/check" className="flex items-center justify-center gap-2 rounded-2xl bg-brand px-6 py-4 text-lg font-bold text-brand-ink shadow-card hover:brightness-110">
              <span aria-hidden="true">📷</span> {t("checkNow")}
            </Link>
            <Link href="/check?sample=1" className="flex items-center justify-center gap-2 rounded-2xl border border-border bg-surface px-6 py-4 text-lg font-semibold text-ink hover:bg-surface-2">
              <span aria-hidden="true">🖼️</span> {t("trySample")}
            </Link>
          </div>
          <p className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-sm font-semibold text-ink-3">
            <span>✓ {t("free")}</span><span>✓ {t("noInstall")}</span><span>✓ {t("languages8")}</span>
          </p>
        </div>
        <PhonePreview />
      </section>

      <section aria-labelledby="how" className="pb-14">
        <h2 id="how" className="text-2xl font-extrabold text-ink">{t("howItWorks")}</h2>
        <ol className="mt-5 grid gap-4 sm:grid-cols-3">
          {FLOW.map((f, i) => (
            <li key={f.title} className="relative rounded-3xl border border-border bg-surface p-5 shadow-card">
              <div className="flex items-center gap-3">
                <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-soft text-3xl" aria-hidden="true">{f.icon}</span>
                <span className="text-sm font-bold text-ink-3">{t("step")} {i + 1}</span>
              </div>
              <h3 className="mt-3 text-lg font-bold text-ink">{t(f.title)}</h3>
              <p className="mt-1 text-sm leading-relaxed text-ink-2">{t(f.text)}</p>
              {i < FLOW.length - 1 && (
                <span className="absolute -right-4 top-1/2 z-10 hidden h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full border border-border bg-surface text-ink-3 sm:flex" aria-hidden="true">→</span>
              )}
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="answers" className="pb-14">
        <h2 id="answers" className="text-2xl font-extrabold text-ink">{t("kinds")}</h2>
        <p className="mt-1 max-w-2xl text-ink-2">{t("kindsSub")}</p>
        <div className="mt-5 grid gap-4 sm:grid-cols-3">
          {OUTCOMES.map((o) => (
            <div key={o.title} className="rounded-3xl border border-border bg-surface p-5 shadow-card">
              <span className={`flex h-14 w-14 items-center justify-center rounded-full text-3xl ${o.tone}`} aria-hidden="true">{o.icon}</span>
              <h3 className="mt-3 text-lg font-bold text-ink">{t(o.title)}</h3>
              <p className="mt-1 text-sm leading-relaxed text-ink-2">{t(o.text)}</p>
            </div>
          ))}
        </div>
      </section>

      <section aria-labelledby="why" className="pb-14">
        <h2 id="why" className="text-2xl font-extrabold text-ink">Why honesty matters</h2>
        <p className="mt-1 max-w-2xl text-ink-2">
          Measured on {R.fieldTestPhotos} real field photos that none of the models saw during training.
        </p>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat tone="red" value={pct(R.labOnlyFieldAccuracy)} label="A typical lab-trained model"
            note={`${pct(R.labAccuracy)} right on lab photos, but only ${pct(R.labOnlyFieldAccuracy)} on ${R.labOnlyTestPhotos} field photos, while ${pct(R.labOnlyFieldConfidence)} sure of itself.`} />
          <Stat value={pct(R.finalFieldAccuracy)} label="Our model's top answer"
            note={`${pct(R.tanzaniaAccuracy)} on farm photos from Tanzania, ${pct(R.plantdocAccuracy)} on harder, more varied web photos.`} />
          <Stat value={pct(R.coverage)} label="Shortlist contains the right disease"
            note={`Target ${pct(R.coverageTarget)}, checked separately for each crop. On average ${R.avgShortlist.toFixed(1)} diseases in the shortlist.`} />
          <Stat value={pct(R.accuracyWhenAnswered)} label="Right when it answers alone"
            note={`It answers about ${pct(R.answeredByAssistant)} of photos itself and sends the rest to an expert.`} />
        </div>
      </section>

      <section className="mb-16 flex flex-col items-start gap-6 rounded-3xl bg-brand px-6 py-10 text-brand-ink sm:flex-row sm:items-center sm:px-10">
        <span className="text-6xl" aria-hidden="true">🌱</span>
        <div className="flex-1">
          <h2 className="text-2xl font-bold">{t("tryOwn")}</h2>
          <p className="mt-2 max-w-xl opacity-90">
            {t("tryOwnT")}
          </p>
        </div>
        <Link href="/check" className="rounded-2xl bg-surface px-6 py-3 font-bold text-brand hover:bg-brand-soft">
          📷 {t("checkLeaf")}
        </Link>
      </section>
    </div>
  );
}
