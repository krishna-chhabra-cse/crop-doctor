"use client";

// Picture-first building blocks for farmers: every important fact is shown as an icon, colour or shape AND words.
import { useEffect, useState } from "react";
import type { Disease, Urgency } from "@/lib/api";
import { useT, type Key } from "@/lib/i18n";
import { REFERENCES } from "@/lib/references";

/* ---------- Status hero: one big symbol that says what kind of answer this is ---------- */
const HERO: Record<string, { icon: string; ring: string; title: Key }> = {
  healthy: { icon: "✅", ring: "bg-brand-soft text-brand", title: "heroHealthy" },
  diagnosis: { icon: "🔎", ring: "bg-amber-soft text-amber", title: "heroDisease" },
  urgent: { icon: "🚨", ring: "bg-red-soft text-red", title: "heroDisease" },
  question: { icon: "❓", ring: "bg-blue-soft text-blue", title: "heroQuestion" },
  expert: { icon: "🧑‍🌾", ring: "bg-blue-soft text-blue", title: "heroExpert" },
  answered: { icon: "🎓", ring: "bg-brand-soft text-brand", title: "heroAnswered" },
  retake: { icon: "📷", ring: "bg-amber-soft text-amber", title: "heroRetake" },
  unfamiliar: { icon: "⚠️", ring: "bg-amber-soft text-amber", title: "unfamiliar" },
};
export type HeroKind = "healthy" | "diagnosis" | "urgent" | "question" | "expert" | "answered" | "retake" | "unfamiliar";

export function StatusHero({ kind, photo, crop }: { kind: HeroKind; photo?: string; crop: string }) {
  const h = HERO[kind];
  const t = useT();
  return (
    <div className="flex items-center gap-4">
      <div className="relative shrink-0">
        {photo ? (
          <img src={photo} alt={`Your ${crop} leaf`} className="h-24 w-24 rounded-3xl object-cover shadow-card sm:h-28 sm:w-28" />
        ) : (
          <div className="h-24 w-24 rounded-3xl bg-surface-2" />
        )}
        <span className={`absolute -bottom-2 -right-2 flex h-11 w-11 items-center justify-center rounded-full border-4 border-surface text-xl ${h.ring}`} aria-hidden="true">
          {h.icon}
        </span>
      </div>
      <div className="min-w-0">
        <p className="text-sm font-semibold uppercase tracking-wide text-ink-3">{t.hi ? `${t(crop === "potato" ? "potato" : "tomato")} का ${t("leaf")}` : `${crop} leaf`}</p>
        <p className="text-xl font-extrabold leading-tight text-ink sm:text-2xl">{t(h.title)}</p>
      </div>
    </div>
  );
}

/* ---------- Confidence: 10 dots are easier to read than a percentage ---------- */
export function ConfidenceDots({ p, tone = "brand" }: { p: number; tone?: "brand" | "leaf" }) {
  const t = useT();
  const filled = Math.max(1, Math.round(p * 10));
  const word = t(p >= 0.9 ? "veryLikely" : p >= 0.7 ? "likely" : p >= 0.5 ? "possible" : "lessLikely");
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1" aria-label={`${word}: ${Math.round(p * 100)} out of 100`}>
      <div className="flex gap-1" aria-hidden="true">
        {Array.from({ length: 10 }, (_, i) => (
          <span key={i} className={`h-3 w-3 rounded-full ${i < filled ? (tone === "brand" ? "bg-brand" : "bg-leaf") : "bg-surface-2 ring-1 ring-border"}`} />
        ))}
      </div>
      <span className="text-sm font-semibold text-ink-2">{word} · {Math.round(p * 100)}%</span>
    </div>
  );
}

/* ---------- Urgency: a traffic light with a clock ---------- */
const LEVELS: { key: string; word: Key; icon: string; on: string }[] = [
  { key: "routine", word: "canWait", icon: "🟢", on: "bg-brand text-brand-ink" },
  { key: "soon", word: "thisWeek", icon: "🟠", on: "bg-amber text-background" },
  { key: "urgent", word: "today", icon: "🔴", on: "bg-red text-background" },
];

export function UrgencyLight({ u }: { u: Urgency }) {
  const t = useT();
  if (u.level === "none") return null;
  const box = u.level === "urgent" ? "border-red/40 bg-red-soft" : u.level === "soon" ? "border-amber/40 bg-amber-soft" : "border-blue/30 bg-blue-soft";
  const ink = u.level === "urgent" ? "text-red" : u.level === "soon" ? "text-amber" : "text-blue";
  return (
    <div className={`rounded-2xl border p-4 ${box}`}>
      <div className="flex items-center gap-3">
        <span className="text-3xl" aria-hidden="true">⏰</span>
        <div>
          <p className={`text-lg font-extrabold leading-tight ${ink}`}>{t("actWithin", { t: t.server(u.act_within) })}</p>
          <p className="text-sm text-ink-2">{t.server(u.why)}</p>
        </div>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-1.5" role="img" aria-label={`Urgency: ${u.level}`}>
        {LEVELS.map((l) => (
          <div key={l.key} className={`rounded-xl px-2 py-1.5 text-center text-xs font-bold ${u.level === l.key ? l.on : "bg-surface/70 text-ink-3"}`}>
            <span aria-hidden="true">{l.icon}</span> {t(l.word)}
          </div>
        ))}
      </div>
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
    <div className="flex items-center gap-4 rounded-2xl bg-surface-2 p-3">
      <svg viewBox="0 0 100 104" className="h-20 w-20 shrink-0" role="img" aria-label={`About ${pct}% of the leaf is damaged`}>
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
        <p className="font-bold text-ink">{word}</p>
        <p className="text-sm text-ink-2">{t("dmgAbout", { p: pct })}</p>
        <p className="text-xs text-ink-3">{t("dmgNote")}</p>
      </div>
    </div>
  );
}

/* ---------- What causes it and how fast it spreads ---------- */
function causeOf(cause?: string | null): { icon: string; word: Key } | null {
  const c = (cause ?? "").toLowerCase();
  if (c.includes("whitefl")) return { icon: "🪰", word: "cWhitefly" };
  if (c.includes("virus")) return { icon: "🧬", word: "cVirus" };
  if (c.includes("bacteri")) return { icon: "🦠", word: "cBacteria" };
  if (c.includes("water mould")) return { icon: "💧", word: "cWater" };
  if (c.includes("fung")) return { icon: "🍄", word: "cFungus" };
  return null;
}
const SPREAD: Record<string, { icon: string; word: Key; bars: number }> = {
  fast: { icon: "🔥", word: "spFast", bars: 3 },
  medium: { icon: "🌬️", word: "spMedium", bars: 2 },
  virus_insect: { icon: "🪰", word: "spInsect", bars: 2 },
  virus_contact: { icon: "🖐️", word: "spContact", bars: 2 },
};

export function DiseaseFacts({ d }: { d: Disease }) {
  const t = useT();
  const cause = causeOf(d.cause);
  const spread = d.spread ? SPREAD[d.spread] : undefined;
  if (!cause && !spread && !d.signs) return null;
  return (
    <div className="grid gap-2 sm:grid-cols-2">
      {cause && (
        <Fact icon={cause.icon} label={t("causedBy")} value={t(cause.word)} />
      )}
      {spread && (
        <Fact icon={spread.icon} label={t("spreads")} value={t(spread.word)}>
          <span className="mt-1 flex gap-1" aria-hidden="true">
            {[1, 2, 3].map((i) => <span key={i} className={`h-1.5 w-6 rounded-full ${i <= spread.bars ? "bg-amber" : "bg-border"}`} />)}
          </span>
        </Fact>
      )}
      {d.signs && (
        <div className="sm:col-span-2">
          <Fact icon="👁️" label={t("recognise")} value={t.hi ? t.server(d.signs) : d.signs.charAt(0).toUpperCase() + d.signs.slice(1)} />
        </div>
      )}
    </div>
  );
}

function Fact({ icon, label, value, children }: { icon: string; label: string; value: string; children?: React.ReactNode }) {
  return (
    <div className="flex items-start gap-3 rounded-2xl bg-surface-2 p-3">
      <span className="text-2xl leading-none" aria-hidden="true">{icon}</span>
      <div className="min-w-0">
        <p className="text-xs font-semibold uppercase tracking-wide text-ink-3">{label}</p>
        <p className="font-semibold leading-snug text-ink">{value}</p>
        {children}
      </div>
    </div>
  );
}

/* ---------- What to do: picture tiles (safe, general steps; details are in the chat reply) ---------- */
export function ActionTiles({ d, healthy, urgent }: { d: Disease | null; healthy: boolean; urgent: boolean }) {
  const t = useT();
  const tiles: { icon: string; text: Key }[] = healthy
    ? [
        { icon: "👀", text: "aWeekly" },
        { icon: "💧", text: "aWater" },
        { icon: "📷", text: "aNewPhoto" },
      ]
    : d?.spread?.startsWith("virus")
      ? [
          { icon: "🪓", text: "aPull" },
          { icon: d.spread === "virus_insect" ? "🪰" : "🧼", text: d.spread === "virus_insect" ? "aWhitefly" : "aWash" },
          { icon: "🚫", text: "aNoCure" },
        ]
      : [
          { icon: "✂️", text: "aRemove" },
          { icon: urgent ? "📢" : "💧", text: urgent ? "aTell" : "aWater" },
          { icon: "🧑‍🌾", text: "aAsk" },
        ];
  return (
    <div>
      <p className="mb-2 text-sm font-bold text-ink">{t("whatToDo")}</p>
      <ol className="grid grid-cols-3 gap-2">
        {tiles.map((tile, i) => (
          <li key={tile.text} className="flex flex-col items-center gap-1.5 rounded-2xl border border-border bg-surface p-3 text-center">
            <span className="relative text-3xl" aria-hidden="true">
              {tile.icon}
              <span className="absolute -left-3 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-brand text-[11px] font-bold text-brand-ink">{i + 1}</span>
            </span>
            <span className="text-xs font-semibold leading-snug text-ink sm:text-sm">{t(tile.text)}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

/* ---------- Read a reply aloud in the farmer's language ---------- */
const LANG: Record<string, string> = {
  English: "en-IN", Hindi: "hi-IN", Tamil: "ta-IN", Telugu: "te-IN", Marathi: "mr-IN",
  Kannada: "kn-IN", Bengali: "bn-IN", Punjabi: "pa-IN",
};

export function ListenButton({ text, language }: { text: string; language: string }) {
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
  return (
    <button type="button" onClick={toggle}
      className="mt-2 inline-flex items-center gap-1.5 rounded-full bg-surface-2 px-3 py-1.5 text-sm font-bold text-ink hover:bg-brand-soft hover:text-brand"
      aria-pressed={speaking}>
      <span aria-hidden="true">{speaking ? "⏹️" : "🔊"}</span>{t(speaking ? "stop" : "listen")}
    </button>
  );
}

/* ---------- Small picture for follow-up question options ---------- */
export function optionIcon(text: string): string {
  const t = text.toLowerCase();
  if (t.includes("ring")) return "🎯";
  if (t.includes("wet") || t.includes("water")) return "💧";
  if (t.includes("fuzz") || t.includes("mould") || t.includes("mold") || t.includes("powder")) return "☁️";
  if (t.includes("yellow")) return "🟡";
  if (t.includes("curl")) return "🌀";
  if (t.includes("mosaic") || t.includes("patch") || t.includes("mottl")) return "🧩";
  if (t.includes("small") || t.includes("tiny") || t.includes("dot")) return "⚫";
  if (t.includes("spot")) return "🟤";
  if (t.includes("insect") || t.includes("fly") || t.includes("flies")) return "🪰";
  return "🍃";
}

export const EXTENT_ICON: Record<string, string> = { few: "🍃", some: "🪴", many: "🌾" };

/* ---------- Reference photos: "Does your leaf look like this?" ---------- */
export function ReferencePhotos({ diseases, single = false }: { diseases: Disease[]; single?: boolean }) {
  const t = useT();
  const items = diseases.filter((d) => REFERENCES[d.label]);
  if (!items.length) return null;
  return (
    <div>
      <p className="mb-2 text-sm font-bold text-ink">
        {single ? t("typicalLook") : t("compareTitle")}
      </p>
      <div className={`grid gap-2 ${single ? "grid-cols-1" : items.length > 2 ? "grid-cols-3" : "grid-cols-2"}`}>
        {items.map((d) => (
          <figure key={d.label} className={`overflow-hidden rounded-2xl border border-border bg-surface ${single ? "flex items-center gap-3 p-2" : ""}`}>
            <img src={REFERENCES[d.label].src} alt={t.server(d.name)} loading="lazy"
              className={single ? "h-24 w-24 shrink-0 rounded-xl object-cover" : "aspect-square w-full object-cover"} />
            <figcaption className={single ? "min-w-0" : "p-2"}>
              <span className="block text-sm font-bold leading-snug text-ink">{t.server(d.name)}</span>
              <span className="mt-0.5 block text-[11px] leading-tight text-ink-3">{t("photoCredit")} {REFERENCES[d.label].credit}</span>
            </figcaption>
          </figure>
        ))}
      </div>
    </div>
  );
}
