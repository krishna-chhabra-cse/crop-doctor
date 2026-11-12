"use client";

// Picture-first building blocks for farmers: every important fact is shown as an icon, a colour or a shape AND words.
// Colour only ever means status: ok (green), soon (amber), urgent (red), ask (blue), expert (violet).
import { useEffect, useState } from "react";
import {
  Ban, BadgeCheck, Bug, Camera, CircleCheck, CircleHelp, Clock, Cloud, Dna, Droplet, Droplets, Eye, Flame, Hand,
  Leaf, Megaphone, Microscope, Puzzle, RotateCcw, ScanSearch, Scissors, Shovel, Sprout, Square, Target, TriangleAlert,
  UserRound, Volume2, Wind, type LucideIcon,
} from "lucide-react";
import type { Disease, Urgency } from "@/lib/api";
import { useT, type Key } from "@/lib/i18n";
import { REFERENCES } from "@/lib/references";

/* ---------- Verdict band: one solid status colour, one icon, one line ---------- */
export type HeroKind = "healthy" | "diagnosis" | "urgent" | "question" | "expert" | "answered" | "retake" | "unfamiliar";

const SOLID = {
  ok: "bg-brand text-on-brand",
  soon: "bg-soon-solid text-on-soon",
  urgent: "bg-urgent-solid text-on-urgent",
  ask: "bg-ask-solid text-on-ask",
  expert: "bg-expert-solid text-on-expert",
} as const;
export type Tone = keyof typeof SOLID;

export const HERO: Record<HeroKind, { icon: LucideIcon; tone: Tone; title: Key }> = {
  healthy: { icon: CircleCheck, tone: "ok", title: "heroHealthy" },
  diagnosis: { icon: TriangleAlert, tone: "soon", title: "heroDisease" },
  urgent: { icon: TriangleAlert, tone: "urgent", title: "heroDisease" },
  question: { icon: CircleHelp, tone: "ask", title: "heroQuestion" },
  expert: { icon: UserRound, tone: "expert", title: "heroExpert" },
  answered: { icon: BadgeCheck, tone: "expert", title: "heroAnswered" },
  retake: { icon: Camera, tone: "soon", title: "heroRetake" },
  unfamiliar: { icon: ScanSearch, tone: "expert", title: "unfamiliar" },
};

/** Status colour for a diagnosis: follows the urgency, so "act today" is always red. */
export function urgencyTone(level?: Urgency["level"]): Tone {
  return level === "urgent" ? "urgent" : level === "soon" ? "soon" : "ok";
}

export function VerdictBand({ kind, tone, label, main, sub }: {
  kind: HeroKind; tone?: Tone; label?: string; main: string; sub?: string;
}) {
  const h = HERO[kind];
  const Icon = h.icon;
  return (
    <div className={`flex items-start gap-3 rounded-xl px-4 py-4 ${SOLID[tone ?? h.tone]}`} role="status">
      <Icon className="mt-0.5 h-8 w-8 shrink-0" strokeWidth={2.25} aria-hidden="true" />
      <div className="min-w-0">
        {label && <p className="text-sm font-semibold">{label}</p>}
        <p className="text-[22px] font-bold leading-7">{main}</p>
        {sub && <p className="mt-0.5 font-semibold">{sub}</p>}
      </div>
    </div>
  );
}

/* ---------- Confidence: 10 neutral dots are easier to read than a percentage ---------- */
export function ConfidenceDots({ p }: { p: number }) {
  const t = useT();
  const filled = Math.max(1, Math.round(p * 10));
  const word = t(p >= 0.9 ? "veryLikely" : p >= 0.7 ? "likely" : p >= 0.5 ? "possible" : "lessLikely");
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1" aria-label={`${word}: ${Math.round(p * 100)} out of 100`}>
      <div className="flex gap-1" aria-hidden="true">
        {Array.from({ length: 10 }, (_, i) => (
          <span key={i} className={`h-2.5 w-2.5 rounded-full ${i < filled ? "bg-ink-2" : "bg-surface-2 ring-1 ring-border"}`} />
        ))}
      </div>
      <span className="text-sm font-semibold text-ink-2">{word} · {Math.round(p * 100)}%</span>
    </div>
  );
}

/* ---------- Urgency: three segments, the active one filled, plus the reason ---------- */
const LEVELS: { key: Urgency["level"]; word: Key; tone: Tone }[] = [
  { key: "routine", word: "canWait", tone: "ok" },
  { key: "soon", word: "thisWeek", tone: "soon" },
  { key: "urgent", word: "today", tone: "urgent" },
];

export function UrgencyLight({ u }: { u: Urgency }) {
  const t = useT();
  if (u.level === "none") return null;
  return (
    <div>
      <div className="grid grid-cols-3 gap-1.5" role="img" aria-label={`${t("actWithin", { t: t.server(u.act_within) })}`}>
        {LEVELS.map((l) => (
          <div key={l.key} className={`flex min-h-10 items-center justify-center rounded-lg px-1 text-center text-sm font-semibold ${
            u.level === l.key ? SOLID[l.tone] : "bg-surface-2 text-ink-3"}`}>
            {t(l.word)}
          </div>
        ))}
      </div>
      <p className="mt-2 flex items-start gap-2 text-ink-2">
        <Clock className="mt-1 h-5 w-5 shrink-0" aria-hidden="true" />{t.server(u.why)}
      </p>
    </div>
  );
}

/* ---------- Leaf damage: a leaf that fills up brown ---------- */
const LEAF = "M50 6C20 26 10 58 26 86c6 10 16 14 24 14s18-4 24-14C90 58 80 26 50 6Z";
export function LeafDamage({ fraction }: { fraction: number }) {
  const t = useT();
  const pct = Math.round(Math.min(Math.max(fraction, 0), 1) * 100);
  const word = t(pct < 10 ? "dmgLittle" : pct < 30 ? "dmgSome" : pct < 60 ? "dmgLot" : "dmgBad");
  return (
    <div className="flex items-center gap-4 py-3">
      <svg viewBox="0 0 100 104" className="h-16 w-16 shrink-0" role="img" aria-label={t("dmgAbout", { p: pct })}>
        <defs>
          <clipPath id="leaf-clip"><path d={LEAF} /></clipPath>
        </defs>
        <path d={LEAF} fill="#3fae5c" />
        <g clipPath="url(#leaf-clip)">
          <rect x="0" y={104 - (104 * pct) / 100} width="100" height="104" fill="#8b5a2b" />
          <circle cx="40" cy={104 - (104 * pct) / 100} r="6" fill="#8b5a2b" />
          <circle cx="64" cy={104 - (104 * pct) / 100 + 2} r="5" fill="#8b5a2b" />
        </g>
        <path d="M50 14v84M50 40l-14-10M50 56l16-12M50 72l-16-10" stroke="#1f6b35" strokeWidth="2.5" fill="none" strokeLinecap="round" opacity="0.6" />
      </svg>
      <div>
        <p className="font-semibold text-ink">{word}</p>
        <p className="text-ink-2">{t("dmgAbout", { p: pct })}</p>
        <p className="text-sm text-ink-3">{t("dmgNote")}</p>
      </div>
    </div>
  );
}

/* ---------- What causes it and how fast it spreads ---------- */
function causeOf(cause?: string | null): { icon: LucideIcon; word: Key } | null {
  const c = (cause ?? "").toLowerCase();
  if (c.includes("whitefl")) return { icon: Bug, word: "cWhitefly" };
  if (c.includes("virus")) return { icon: Dna, word: "cVirus" };
  if (c.includes("bacteri")) return { icon: Microscope, word: "cBacteria" };
  if (c.includes("water mould")) return { icon: Droplets, word: "cWater" };
  if (c.includes("fung")) return { icon: Sprout, word: "cFungus" };
  return null;
}
const SPREAD: Record<string, { icon: LucideIcon; word: Key; bars: number }> = {
  fast: { icon: Flame, word: "spFast", bars: 3 },
  medium: { icon: Wind, word: "spMedium", bars: 2 },
  virus_insect: { icon: Bug, word: "spInsect", bars: 2 },
  virus_contact: { icon: Hand, word: "spContact", bars: 2 },
};

export function hasFacts(d: Disease) {
  return !!(causeOf(d.cause) || (d.spread && SPREAD[d.spread]) || d.signs);
}

export function DiseaseFacts({ d }: { d: Disease }) {
  const t = useT();
  const cause = causeOf(d.cause);
  const spread = d.spread ? SPREAD[d.spread] : undefined;
  if (!cause && !spread && !d.signs) return null;
  return (
    <ul className="divide-y divide-border">
      {cause && <Fact icon={cause.icon} label={t("causedBy")} value={t(cause.word)} />}
      {spread && (
        <Fact icon={spread.icon} label={t("spreads")} value={t(spread.word)}>
          <span className="mt-1 flex gap-1" aria-hidden="true">
            {[1, 2, 3].map((i) => <span key={i} className={`h-1.5 w-6 rounded-full ${i <= spread.bars ? "bg-ink-2" : "bg-border"}`} />)}
          </span>
        </Fact>
      )}
      {d.signs && (
        <Fact icon={Eye} label={t("recognise")} value={t.hi ? t.server(d.signs) : d.signs.charAt(0).toUpperCase() + d.signs.slice(1)} />
      )}
    </ul>
  );
}

function Fact({ icon: Icon, label, value, children }: { icon: LucideIcon; label: string; value: string; children?: React.ReactNode }) {
  return (
    <li className="flex items-start gap-3 py-3">
      <Icon className="mt-0.5 h-6 w-6 shrink-0 text-ink-2" aria-hidden="true" />
      <div className="min-w-0">
        <p className="text-sm text-ink-3">{label}</p>
        <p className="font-semibold leading-snug text-ink">{value}</p>
        {children}
      </div>
    </li>
  );
}

/* ---------- What to do: a numbered list (safe, general steps; details are in the chat reply) ---------- */
export function actionSteps(d: Disease | null, healthy: boolean, urgent: boolean): { icon: LucideIcon; text: Key }[] {
  if (healthy)
    return [
      { icon: Eye, text: "aWeekly" },
      { icon: Droplet, text: "aWater" },
      { icon: Camera, text: "aNewPhoto" },
    ];
  if (d?.spread?.startsWith("virus"))
    return [
      { icon: Shovel, text: "aPull" },
      d.spread === "virus_insect" ? { icon: Bug, text: "aWhitefly" } : { icon: Hand, text: "aWash" },
      { icon: Ban, text: "aNoCure" },
    ];
  return [
    { icon: Scissors, text: "aRemove" },
    urgent ? { icon: Megaphone, text: "aTell" } : { icon: Droplet, text: "aWater" },
    { icon: UserRound, text: "aAsk" },
  ];
}

export function ActionList({ steps }: { steps: { icon: LucideIcon; text: Key }[] }) {
  const t = useT();
  return (
    <section aria-labelledby="todo">
      <h2 id="todo" className="text-lg font-semibold text-ink">{t("whatToDo")}</h2>
      <ol className="mt-1 divide-y divide-border">
        {steps.map((s, i) => (
          <li key={s.text} className="flex min-h-14 items-center gap-3 py-2">
            <span className="w-5 shrink-0 text-right text-lg font-bold text-ink-3" aria-hidden="true">{i + 1}</span>
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-surface-2 text-ink" aria-hidden="true">
              <s.icon className="h-5 w-5" />
            </span>
            <span className="text-lg leading-snug text-ink">{t(s.text)}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

/* ---------- Read text aloud ---------- */
const LANG: Record<string, string> = {
  English: "en-IN", Hindi: "hi-IN", Tamil: "ta-IN", Telugu: "te-IN", Marathi: "mr-IN",
  Kannada: "kn-IN", Bengali: "bn-IN", Punjabi: "pa-IN",
};

export function ListenButton({ text, language, big = false }: { text: string; language: string; big?: boolean }) {
  const [speaking, setSpeaking] = useState(false);
  const [supported, setSupported] = useState(false);
  const t = useT();
  useEffect(() => {
    // Feature check after mount (speech synthesis only exists in the browser).
    const ok = typeof window !== "undefined" && "speechSynthesis" in window;
    const id = requestAnimationFrame(() => setSupported(ok));
    return () => {
      cancelAnimationFrame(id);
      if (ok) window.speechSynthesis.cancel();
    };
  }, []);
  if (!supported) return null;
  const toggle = () => {
    const s = window.speechSynthesis;
    if (speaking) {
      s.cancel();
      setSpeaking(false);
      return;
    }
    s.cancel();
    const clean = text.replace(/\*\*/g, "").replace(/^Sources:[\s\S]*$/m, "").replace(/https?:\/\/\S+/g, "");
    const u = new SpeechSynthesisUtterance(clean);
    u.lang = LANG[language] ?? "en-IN";
    u.rate = 0.95;
    const voice = s.getVoices().find((v) => v.lang === u.lang) ?? s.getVoices().find((v) => v.lang.startsWith(u.lang.slice(0, 2)));
    if (voice) u.voice = voice;
    u.onend = u.onerror = () => setSpeaking(false);
    s.speak(u);
    setSpeaking(true);
  };
  const Icon = speaking ? Square : Volume2;
  return (
    <button type="button" onClick={toggle} aria-pressed={speaking}
      className={big
        ? "flex min-h-14 w-full items-center justify-center gap-2 rounded-xl border-2 border-ink bg-surface px-4 text-lg font-semibold text-ink hover:bg-surface-2"
        : "mt-2 inline-flex min-h-12 items-center gap-2 rounded-xl border border-border bg-surface px-4 font-semibold text-ink hover:bg-surface-2"}>
      <Icon className={big ? "h-6 w-6" : "h-5 w-5"} aria-hidden="true" />
      {t(speaking ? "stop" : big ? "listenAnswer" : "listen")}
    </button>
  );
}

/* ---------- Small picture for follow-up question options ---------- */
export function optionIcon(text: string): LucideIcon {
  const t = text.toLowerCase();
  if (t.includes("ring")) return Target;
  if (t.includes("wet") || t.includes("water")) return Droplets;
  if (t.includes("fuzz") || t.includes("mould") || t.includes("mold") || t.includes("powder")) return Cloud;
  if (t.includes("curl")) return RotateCcw;
  if (t.includes("mosaic") || t.includes("patch") || t.includes("mottl")) return Puzzle;
  if (t.includes("insect") || t.includes("fly") || t.includes("flies")) return Bug;
  if (t.includes("no,") || t.includes("normal") || t.includes("nothing")) return CircleCheck;
  return Leaf;
}

/** Few / some / many: 1, 3 or 6 leaves. */
export function ExtentIcon({ value }: { value: string }) {
  const n = value === "many" ? 6 : value === "some" ? 3 : 1;
  return (
    <span className="grid h-12 grid-cols-3 place-content-center gap-0.5 text-ok" aria-hidden="true">
      {Array.from({ length: n }, (_, i) => <Leaf key={i} className="h-5 w-5" />)}
    </span>
  );
}

/* ---------- Your photo next to a typical photo of the disease ---------- */
export function PhotoCompare({ photo, disease }: { photo?: string; disease: Disease | null }) {
  const t = useT();
  const ref = disease ? REFERENCES[disease.label] : undefined;
  if (!photo && !ref) return null;
  return (
    <div className="grid grid-cols-2 gap-3">
      {photo && (
        <figure>
          <img src={photo} alt={t("yourPhoto")} className="aspect-[4/3] w-full rounded-lg object-cover" />
          <figcaption className="mt-1 text-sm font-semibold text-ink">{t("yourLeaf")}</figcaption>
        </figure>
      )}
      {ref && disease && (
        <figure>
          <img src={ref.src} alt={t.server(disease.name)} loading="lazy" className="aspect-[4/3] w-full rounded-lg object-cover" />
          <figcaption className="mt-1 text-sm leading-snug">
            <span className="block font-semibold text-ink">{t("typicalLook")}</span>
            <span className="block text-ink-3">{t("photoCredit")} {ref.credit}</span>
          </figcaption>
        </figure>
      )}
    </div>
  );
}

/* ---------- Reference photos: "Does your leaf look like this?" ---------- */
export function ReferencePhotos({ diseases }: { diseases: Disease[] }) {
  const t = useT();
  const items = diseases.filter((d) => REFERENCES[d.label]);
  if (!items.length) return null;
  return (
    <div>
      <p className="mb-2 font-semibold text-ink">{t("compareTitle")}</p>
      <div className={`grid gap-3 ${items.length > 2 ? "grid-cols-3" : "grid-cols-2"}`}>
        {items.map((d) => (
          <figure key={d.label}>
            <img src={REFERENCES[d.label].src} alt={t.server(d.name)} loading="lazy" className="aspect-square w-full rounded-lg object-cover" />
            <figcaption className="mt-1 text-sm leading-snug">
              <span className="block font-semibold text-ink">{t.server(d.name)}</span>
              <span className="block text-ink-3">{t("photoCredit")} {REFERENCES[d.label].credit}</span>
            </figcaption>
          </figure>
        ))}
      </div>
    </div>
  );
}
