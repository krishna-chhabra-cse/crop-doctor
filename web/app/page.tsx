"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { Camera, Check, CircleCheck, CircleHelp, Image as ImageIcon, MessageCircle, ScanSearch, UserRound, type LucideIcon } from "lucide-react";
import { useT, type Key } from "@/lib/i18n";
import { RESULTS as R } from "@/lib/results";

// Round DOWN so a result is never overstated (99.5% shows as 99%, not 100%).
const pct = (x: number) => `${Math.floor(x * 100 + 1e-9)}%`;

const WRAP = "mx-auto w-full max-w-[1280px] px-5 sm:px-8";

/* Parts of a section rise into place once as it enters the screen. Visible by default without script. */
function Reveal({ children, className = "", delay = 0 }: { children: ReactNode; className?: string; delay?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<"idle" | "wait" | "in">("idle");
  useEffect(() => {
    const el = ref.current;
    if (!el || !("IntersectionObserver" in window)) return;
    if (el.getBoundingClientRect().top < window.innerHeight * 0.9) return; // already on screen: leave it shown
    setState("wait");
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setState("in"); io.disconnect(); }
    }, { rootMargin: "0px 0px -10% 0px" });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div ref={ref} className={`reveal ${state === "wait" ? "reveal-wait" : ""} ${className}`} style={{ "--d": `${delay}ms` } as CSSProperties}>
      {children}
    </div>
  );
}

type Kind = "sure" | "almost" | "notSure";

/* The hero fragment: a farmer's chat with Crop Doctor about one real field photo.
   Answers come from crop_doctor/knowledge (diseases.json and docs/potato_early_blight.md). */
function PhoneChat({ kind }: { kind: Kind }) {
  const t = useT();
  const farmer = "msg ml-auto max-w-[84%] rounded-[20px] rounded-br-md bg-brand px-3.5 py-2.5 text-on-brand";
  const model = "msg max-w-[90%] rounded-[20px] rounded-bl-md bg-surface px-3.5 py-2.5 text-ink";
  return (
    <div data-ui className="w-full max-w-[360px]">
      <div className="flex h-[560px] flex-col overflow-hidden rounded-3xl bg-surface-2 text-[15px] leading-snug">
        <div className="flex items-center gap-2.5 bg-surface-2 px-4 py-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-full bg-ok-soft text-ok" aria-hidden="true"><ScanSearch className="h-5 w-5" /></span>
          <span className="font-bold text-ink">Crop Doctor</span>
        </div>
        <div key={kind} className="flex flex-1 flex-col justify-end gap-2.5 overflow-hidden bg-background px-3 py-4" aria-live="polite">
          <div className={`${farmer} p-1.5`} style={{ "--i": 0 } as CSSProperties}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/landing/diag_potato.jpg" alt={t("yourLeaf")} width={800} height={615} className="aspect-[4/3] w-full rounded-[14px] object-cover" />
            <p className="px-2 pb-1 pt-2">{t("chatQ1")}</p>
          </div>
          {kind === "sure" && (
            <>
              <div className={model} style={{ "--i": 1 } as CSSProperties}>
                <p className="flex items-center gap-1.5 text-sm font-semibold text-ok"><CircleCheck className="h-4 w-4" aria-hidden="true" /> {t("sure")}</p>
                <p className="mt-0.5 text-base font-bold">{t.server("Potato early blight")}</p>
                <p className="mt-1 text-ink-2">{t("chatCause")}</p>
              </div>
              <p className={farmer} style={{ "--i": 2 } as CSSProperties}>{t("chatQ2")}</p>
              <div className={model} style={{ "--i": 3 } as CSSProperties}>
                <p>{t("chatA2")}</p>
                <p className="mt-1.5 text-sm font-semibold text-soon">{t("chatKvk")}</p>
              </div>
            </>
          )}
          {kind === "almost" && (
            <div className={model} style={{ "--i": 1 } as CSSProperties}>
              <p className="flex items-center gap-1.5 text-sm font-semibold text-ask"><CircleHelp className="h-4 w-4" aria-hidden="true" /> {t("almost")}</p>
              <p className="mt-1">{t.server("Look closely at the spots. Which looks more like your leaf?")}</p>
              <div className="mt-2.5 space-y-2">
                <span className="block rounded-xl border border-ask bg-ask-soft px-3 py-2 font-semibold text-ask">{t.server("Bigger brown spots with rings inside, like a target")}</span>
                <span className="block rounded-xl border border-border px-3 py-2 text-ink">{t.server("Many small round spots with dark edges and pale centres")}</span>
              </div>
            </div>
          )}
          {kind === "notSure" && (
            <div className={model} style={{ "--i": 1 } as CSSProperties}>
              <p className="flex items-center gap-1.5 text-sm font-semibold text-expert"><UserRound className="h-4 w-4" aria-hidden="true" /> {t("notSure")}</p>
              <p className="mt-1">{t("chatNotSure")}</p>
              <p className="mt-2 inline-flex items-center gap-2 rounded-full bg-expert-soft px-3 py-1 text-sm font-semibold text-expert">
                <span className="dot-pulse inline-flex gap-0.5" aria-hidden="true"><span>•</span><span>•</span><span>•</span></span> {t("waitingExpert")}
              </p>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2 bg-surface-2 px-3 py-3" aria-hidden="true">
          <span className="flex-1 rounded-full bg-surface px-4 py-2.5 text-ink-2">{t("chatPlaceholder")}</span>
          <span className="flex h-10 w-10 items-center justify-center rounded-full bg-brand text-on-brand"><MessageCircle className="h-5 w-5" /></span>
        </div>
      </div>
    </div>
  );
}

const KINDS: { id: Kind; label: Key; icon: LucideIcon; on: string }[] = [
  { id: "sure", label: "sure", icon: CircleCheck, on: "bg-ok text-on-brand" },
  { id: "almost", label: "almost", icon: CircleHelp, on: "bg-ask-solid text-on-ask" },
  { id: "notSure", label: "notSure", icon: UserRound, on: "bg-expert-solid text-on-expert" },
];

function Hero() {
  const t = useT();
  const [kind, setKind] = useState<Kind>("sure");
  const lines = t("heroTitle").split(/(?<=[.।])\s+/);
  return (
    <section className={`${WRAP} grid items-center gap-12 pb-24 pt-8 lg:grid-cols-[1fr_auto] lg:gap-20 lg:pb-32 lg:pt-6`}>
      <div>
        <h1 className="text-[28px] font-bold leading-[1.08] tracking-[-0.03em] text-ink sm:text-5xl lg:text-[60px]">
          {lines.map((l, i) => (
            <span key={i} className="line-mask"><span className="line" style={{ "--l": i } as CSSProperties}>{l}</span></span>
          ))}
        </h1>
        <p className="hero-after mt-10 max-w-[34rem] text-lg leading-relaxed text-ink sm:text-xl">{t("heroText")}</p>
        <div className="hero-after mt-10 flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-5">
          <Link href="/check" className="press flex min-h-14 items-center justify-center gap-2 rounded-full bg-brand px-8 text-lg font-semibold text-on-brand">
            <Camera className="h-6 w-6" aria-hidden="true" /> {t("checkNow")}
          </Link>
          <Link href="/check?sample=1" className="press flex min-h-12 items-center justify-center gap-2 px-2 font-semibold text-ink underline underline-offset-4 hover:text-brand">
            <ImageIcon className="h-5 w-5" aria-hidden="true" /> {t("trySample")}
          </Link>
        </div>
        <ul className="hero-after mt-8 flex flex-wrap gap-x-6 gap-y-2 text-ink">
          {(["free", "noInstall", "languages8"] as const).map((k) => (
            <li key={k} className="flex items-center gap-2"><Check className="h-5 w-5 text-ok" aria-hidden="true" />{t(k)}</li>
          ))}
        </ul>
      </div>

      <div className="flex flex-col items-center gap-5">
        <PhoneChat kind={kind} />
        <div role="radiogroup" aria-label={t("liveLabel")} className="flex w-full max-w-[360px] gap-1 rounded-full bg-surface-2 p-1">
          {KINDS.map((k) => (
            <button key={k.id} type="button" role="radio" aria-checked={kind === k.id} onClick={() => setKind(k.id)}
              className={`press flex min-h-11 flex-1 items-center justify-center gap-1 whitespace-nowrap rounded-full px-1.5 text-sm font-semibold ${kind === k.id ? k.on : "text-ink hover:bg-surface"}`}>
              <k.icon className="h-4 w-4" aria-hidden="true" /> {t(k.label)}
            </button>
          ))}
        </div>
        <p className="max-w-[360px] text-center text-sm text-ink-2">{t("sampleCaption")}</p>
      </div>
    </section>
  );
}

/* How it works: one reading column, run-in phrases, real field photos as evidence. */
function HowItWorks() {
  const t = useT();
  const steps: { title: Key; text: Key; pics: string[] }[] = [
    { title: "flow1t", text: "flow1", pics: [] },
    { title: "flow2t", text: "flow2", pics: ["/reference/potato_early_blight.jpg", "/reference/potato_late_blight.jpg", "/reference/potato_healthy.jpg"] },
    { title: "flow3t", text: "flow3", pics: [] },
  ];
  return (
    <section aria-labelledby="how" className="bg-surface py-28 lg:py-40">
      <div className={`${WRAP} grid gap-12 lg:grid-cols-[1fr_560px] lg:gap-20`}>
        {/* Left: the heading and the photo a farmer takes. */}
        <div>
          <Reveal><h2 id="how" className="text-[32px] font-bold leading-tight tracking-[-0.02em] text-ink lg:text-5xl">{t("howItWorks")}</h2></Reveal>
          <Reveal delay={80} className="mt-8">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/landing/question.jpg" alt="" loading="lazy" width={800} height={600} className="aspect-[4/3] w-full rounded-3xl object-cover lg:aspect-[5/4]" />
          </Reveal>
        </div>
        <ol className="space-y-14 lg:pt-24">
          {steps.map((s, i) => (
            <li key={s.title}>
              <Reveal delay={i * 80}>
                <p className="text-lg leading-relaxed text-ink-2"><strong className="font-bold text-ink">{t(s.title)}.</strong> {t(s.text)}</p>
              </Reveal>
              {s.pics.length === 1 && (
                <Reveal delay={i * 80 + 80} className="mt-5">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={s.pics[0]} alt="" loading="lazy" width={800} height={450} className="aspect-video w-full rounded-2xl object-cover" />
                </Reveal>
              )}
              {s.pics.length > 1 && (
                <Reveal delay={i * 80 + 80} className="mt-5 flex gap-3 overflow-x-auto">
                  {s.pics.map((p) => (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img key={p} src={p} alt="" loading="lazy" width={300} height={300} className="h-36 min-w-0 flex-1 rounded-2xl object-cover sm:h-44" />
                  ))}
                </Reveal>
              )}
              {s.title === "flow3t" && (
                <Reveal delay={i * 80 + 80} className="mt-5">
                  <div data-ui className="rounded-2xl bg-background p-5">
                    <p className="flex items-center gap-1.5 text-sm font-semibold text-ok"><CircleCheck className="h-4 w-4" aria-hidden="true" /> {t("sure")}</p>
                    <p className="mt-1 text-xl font-bold text-ink">{t.server("Potato early blight")}</p>
                    <p className="mt-2 leading-relaxed text-ink-2">{t("chatA2")}</p>
                    <p className="mt-2 text-sm font-semibold text-soon">{t("chatKvk")}</p>
                  </div>
                </Reveal>
              )}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

const OUTCOMES: { icon: LucideIcon; tone: string; title: Key; text: Key }[] = [
  { icon: CircleCheck, tone: "bg-ok-soft text-ok", title: "sure", text: "sureT" },
  { icon: CircleHelp, tone: "bg-ask-soft text-ask", title: "almost", text: "almostT" },
  { icon: UserRound, tone: "bg-expert-soft text-expert", title: "notSure", text: "notSureT" },
];

/* Three kinds of answer: a statement on the left, the three as a large run on the right. */
function Answers() {
  const t = useT();
  return (
    <section aria-labelledby="answers" className={`${WRAP} grid gap-12 py-28 lg:grid-cols-[5fr_7fr] lg:gap-20 lg:py-40`}>
      <Reveal>
        <h2 id="answers" className="text-[32px] font-bold leading-tight tracking-[-0.02em] text-ink lg:text-5xl">{t("kinds")}</h2>
        <p className="mt-6 max-w-md text-xl leading-relaxed text-ink">{t("kindsSub")}</p>
      </Reveal>
      <ul className="space-y-12">
        {OUTCOMES.map((o, i) => (
          <li key={o.title}>
            <Reveal delay={i * 90} className="flex gap-5">
              <span className={`flex h-16 w-16 shrink-0 items-center justify-center rounded-full ${o.tone}`} aria-hidden="true"><o.icon className="h-8 w-8" /></span>
              <div>
                <h3 className="text-2xl font-bold text-ink">{t(o.title)}</h3>
                <p className="mt-1 text-lg leading-relaxed text-ink-2">{t(o.text)}</p>
              </div>
            </Reveal>
          </li>
        ))}
      </ul>
    </section>
  );
}

/* One number with its bar and plain sentence. The number leads; its meaning follows as the sentence. */
function Figure({ value, title, note, strong, target }: { value: number; title: string; note: string; strong?: boolean; target?: number }) {
  return (
    <div>
      <p className={`text-6xl font-bold tabular-nums tracking-[-0.03em] lg:text-7xl ${strong ? "text-brand" : "text-ink-2"}`}>{pct(value)}</p>
      <h3 className="mt-2 text-xl font-bold text-ink">{title}</h3>
      <span className="relative mt-4 block h-3 rounded-full bg-surface-2" aria-hidden="true">
        <span className={`block h-3 rounded-full ${strong ? "bg-brand" : "bg-ink-3"}`} style={{ width: pct(value) }} />
        {target !== undefined && <span className="absolute -top-1.5 h-6 w-1 rounded-full bg-ink" style={{ left: pct(target) }} />}
      </span>
      <p className="mt-4 max-w-prose text-lg leading-relaxed text-ink-2">{note}</p>
    </div>
  );
}

function Honesty() {
  const t = useT();
  return (
    <section aria-labelledby="why" className="bg-surface py-28 lg:py-40">
      <div className={WRAP}>
        <Reveal>
          <h2 id="why" className="text-[32px] font-bold leading-tight tracking-[-0.02em] text-ink lg:text-5xl">{t("whyTitle")}</h2>
          <p className="mt-4 text-xl leading-relaxed text-ink">{t("whyTested", { n: R.fieldTestPhotos.toLocaleString("en-IN") })}</p>
        </Reveal>
        <div className="mt-16 grid gap-16 md:grid-cols-2 lg:gap-x-24">
          <Reveal><Figure value={R.labOnlyFieldAccuracy} title={`${t("whyUsualTag")}: ${t("whyFieldLabel")}`}
            note={t("whyFieldNote", { lab: pct(R.labAccuracy), field: pct(R.labOnlyFieldAccuracy), conf: pct(R.labOnlyFieldConfidence) })} /></Reveal>
          {/* Honest numbers rule: lead with the hard 63% on varied photos, not the easy-set average. */}
          <Reveal delay={90}><Figure strong value={R.plantdocAccuracy} title={`${t("whyOursTag")}: ${t("whyFirstLabel")}`}
            note={t("whyFirstNote", { tz: pct(R.tanzaniaAccuracy), pd: pct(R.plantdocAccuracy) })} /></Reveal>
          <Reveal><Figure strong value={R.coverage} target={R.coverageTarget} title={t("whyCoverLabel")}
            note={t("whyCoverNote", { target: pct(R.coverageTarget) })} /></Reveal>
          <Reveal delay={90}><Figure strong value={R.accuracyWhenAnswered} title={t("whyAloneLabel")}
            note={t("whyAloneNote", { answered: pct(R.answeredByAssistant) })} /></Reveal>
        </div>
        <p className="mt-16 text-sm text-ink-2">{t("fieldPhotoCredit")}</p>
      </div>
    </section>
  );
}

/* The close: a full field of brand green with the first step already open. */
function Close() {
  const t = useT();
  return (
    <section aria-labelledby="close" className="bg-brand py-28 text-on-brand lg:py-40">
      <div className={`${WRAP} grid items-end gap-12 lg:grid-cols-[1fr_440px]`}>
        <Reveal>
          <h2 id="close" className="text-[34px] font-bold leading-[1.02] tracking-[-0.03em] sm:text-6xl lg:text-7xl">{t("closeTitle")}</h2>
          <p className="mt-6 max-w-md text-xl leading-relaxed">{t("closeText")}</p>
        </Reveal>
        <Reveal delay={120}>
          <div data-ui className="rounded-3xl bg-background p-6 text-ink">
            <div className="flex items-center gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-full bg-ok-soft text-ok" aria-hidden="true"><Camera className="h-6 w-6" /></span>
              <p className="text-lg font-bold">{t("flow1t")}</p>
            </div>
            <p className="mt-3 leading-relaxed text-ink-2">{t("flow1")}</p>
            <Link href="/check" className="press mt-6 flex min-h-14 items-center justify-center gap-2 rounded-full bg-brand px-6 text-lg font-semibold text-on-brand">
              <Camera className="h-6 w-6" aria-hidden="true" /> {t("checkNow")}
            </Link>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

export default function Home() {
  return (
    <div className="flex-1">
      <Hero />
      <HowItWorks />
      <Answers />
      <Honesty />
      <Close />
    </div>
  );
}
