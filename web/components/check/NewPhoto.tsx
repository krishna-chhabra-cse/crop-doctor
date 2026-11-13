"use client";

import { useEffect, useRef, useState } from "react";
import { api, API_URL, errorKey, type CaseView, type Meta } from "@/lib/api";
import { NATIVE, useT, type Key } from "@/lib/i18n";
import {
  Camera, Check, ChevronDown, CircleCheck, CloudFog, Focus, Image as ImageIcon, Info, Leaf, LoaderCircle, Moon, RotateCcw,
  ScanSearch, Sun, Upload, X, ZoomOut, type LucideIcon,
} from "lucide-react";
import { shrinkPhoto } from "@/lib/photo";
import { REFERENCES } from "@/lib/references";

const CROPS: Record<string, { label: Key; local: string; en: string; emoji: string; photo?: string }> = {
  tomato: { label: "tomato", local: "टमाटर", en: "Tomato", emoji: "🍅", photo: REFERENCES.tomato_healthy?.src },
  potato: { label: "potato", local: "आलू", en: "Potato", emoji: "🥔", photo: REFERENCES.potato_healthy?.src },
};
type Phase = "preparing" | "sending" | "checking";
const PHASES: Phase[] = ["preparing", "sending", "checking"];
const PHASE_ICON: Record<Phase, LucideIcon> = { preparing: ImageIcon, sending: Upload, checking: ScanSearch };
const PHASE_TEXT: Record<Phase, Key> = { preparing: "upPreparing", sending: "upSending", checking: "upChecking" };
const GOOD: { icon: LucideIcon; text: Key }[] = [
  { icon: Sun, text: "daylight" },
  { icon: Leaf, text: "fillPhoto" },
  { icon: Focus, text: "focus" },
];
const BAD: { icon: LucideIcon; text: Key }[] = [
  { icon: CloudFog, text: "blurry" },
  { icon: Moon, text: "tooDark" },
  { icon: ZoomOut, text: "tooFar" },
];

type Props = {
  meta: Meta;
  language: string;
  onLanguage: (l: string) => void;
  onOpened: (c: CaseView) => void;
  showSamples: boolean;
};

function StepTitle({ n, done, children }: { n: number; done: boolean; children: React.ReactNode }) {
  return (
    <h2 className="flex items-center gap-3 text-lg font-semibold text-ink">
      <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full font-semibold ${done ? "bg-brand text-on-brand" : "bg-surface-2 text-ink"}`}>
        {done ? <Check className="h-5 w-5" strokeWidth={3} aria-label={String(n)} /> : n}
      </span>
      {children}
    </h2>
  );
}

export default function NewPhoto({ meta, language, onLanguage, onOpened, showSamples }: Props) {
  const [crop, setCrop] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [phase, setPhase] = useState<Phase | null>(null);       // null = not sending
  const [steps, setSteps] = useState<Phase[]>(PHASES);
  const [progress, setProgress] = useState(0);
  const [slow, setSlow] = useState(false);
  const [busyPreview, setBusyPreview] = useState<string | null>(null);
  const [error, setError] = useState<Key | null>(null);
  const [lastSample, setLastSample] = useState<{ file: string; crop: string } | null>(null);   // what "Try again" resends
  const samplesRef = useRef<HTMLDetailsElement>(null);
  const t = useT();

  useEffect(() => {
    if (showSamples && samplesRef.current) {
      samplesRef.current.open = true;
      samplesRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [showSamples]);

  useEffect(() => () => {
    if (preview) URL.revokeObjectURL(preview);
  }, [preview]);

  const pick = (f: File | undefined) => {
    if (!f) return;
    setError(null);
    setFile(f);
    setPreview(URL.createObjectURL(f));
  };

  // Honest progress: shrink the photo here, send it (real upload progress), then wait while the server checks it.
  const submit = async (sample?: { file: string; crop: string }) => {
    const form = new FormData();
    form.set("language", language);
    const own = file;
    if (sample) {
      form.set("crop", sample.crop);
      form.set("sample", sample.file);
      setBusyPreview(`${API_URL}/api/samples/${sample.file}`);
      setSteps(PHASES.filter((p) => p !== "preparing"));
    } else {
      if (!crop || !own) return;
      form.set("crop", crop);
      setBusyPreview(preview);
      setSteps(PHASES);
    }
    setLastSample(sample ?? null);
    setError(null);
    setProgress(0);
    setSlow(false);
    let slowTimer: ReturnType<typeof setTimeout> | undefined;
    try {
      if (!sample && own) {
        setPhase("preparing");
        const small = await shrinkPhoto(own);
        form.set("file", small, small === own ? own.name : "photo.jpg");
      }
      setPhase("sending");
      slowTimer = setTimeout(() => setSlow(true), 12000);   // the free server may be starting up
      const c = await api.createCase(form, setProgress, () => setPhase("checking"));
      onOpened(c);
    } catch (e) {
      setError(errorKey(e, "photo"));
      setPhase(null);
    } finally {
      clearTimeout(slowTimer);
    }
  };
  const retry = () => submit(lastSample ?? undefined);

  if (phase) {
    const current = steps.indexOf(phase);
    return (
      <div className="rise py-6">
        <div className="relative mx-auto h-60 w-60">
          <div className="scan-ring absolute inset-0 rounded-full" aria-hidden="true" />
          <div className="absolute inset-[5px] overflow-hidden rounded-full bg-surface-2 ring-4 ring-background">
            {busyPreview && <img src={busyPreview} alt={t("yourPhoto")} className="h-full w-full object-cover" />}
            <div className="scan-sweep absolute inset-x-6 h-0.5 rounded-full bg-brand" aria-hidden="true" />
          </div>
        </div>
        <ol className="mx-auto mt-8 max-w-xs divide-y divide-border rounded-2xl border border-border bg-surface px-4 shadow-card" role="status" aria-live="polite">
          {steps.map((p, i) => {
            const Icon = i < current ? CircleCheck : i === current ? LoaderCircle : PHASE_ICON[p];
            return (
              <li key={p} className={`flex min-h-12 items-center gap-3 ${i <= current ? "text-ink" : "text-ink-3"}`}>
                <Icon className={`h-6 w-6 shrink-0 ${i < current ? "text-ok" : ""} ${i === current ? "spin text-brand" : ""}`} aria-hidden="true" />
                <span className={i === current ? "font-semibold" : ""}>{t(PHASE_TEXT[p])}</span>
              </li>
            );
          })}
        </ol>
        {phase === "sending" && (
          <div className="mx-auto mt-4 h-2 max-w-xs overflow-hidden rounded-full bg-surface-2" role="progressbar"
            aria-label={t("upSending")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress * 100)}>
            <div className="h-full rounded-full bg-brand" style={{ width: `${Math.round(progress * 100)}%` }} />
          </div>
        )}
        {slow && <p className="mx-auto mt-4 max-w-xs text-center text-sm text-ink-2">{t("upSlow")}</p>}
      </div>
    );
  }

  const card = "rounded-2xl border border-border bg-surface p-5 shadow-card";
  return (
    <div className="rise space-y-5">
      <div>
        <h1 className="text-[28px] font-bold leading-[34px] text-ink">{t("checkLeaf")}</h1>
        <p className="mt-1 text-ink-2">{t("stepsSub")}</p>
      </div>

      <section aria-labelledby="s1" className={card}>
        <div id="s1"><StepTitle n={1} done={!!crop}>{t("whichCrop")}</StepTitle></div>
        <div className="mt-4 grid grid-cols-2 gap-3" role="radiogroup" aria-label="Crop">
          {meta.crops.map((c) => {
            const on = crop === c;
            return (
              <button key={c} type="button" role="radio" aria-checked={on} onClick={() => setCrop(c)}
                className={`relative flex min-h-36 flex-col items-start justify-end overflow-hidden rounded-2xl border-2 bg-[#0b130e] p-3 text-left text-white transition ${
                  on ? "border-brand shadow-glow" : "border-transparent hover:border-ink-3"}`}>
                {CROPS[c]?.photo && <img src={CROPS[c].photo} alt="" className={`absolute inset-0 h-full w-full object-cover transition ${on ? "scale-105" : ""}`} />}
                <span className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/30 to-black/0" aria-hidden="true" />
                {on && (
                  <span className="absolute right-2 top-2 flex h-7 w-7 items-center justify-center rounded-full bg-brand text-on-brand" aria-hidden="true">
                    <Check className="h-4 w-4" strokeWidth={3} />
                  </span>
                )}
                <span className="relative text-2xl" aria-hidden="true">{CROPS[c]?.emoji ?? ""}</span>
                <span className="relative text-lg font-semibold">{CROPS[c] ? t(CROPS[c].label) : c}</span>
                <span className="relative text-sm text-white/75">{CROPS[c] ? (t.hi ? CROPS[c].en : CROPS[c].local) : ""}</span>
              </button>
            );
          })}
        </div>
      </section>

      <section aria-labelledby="s2" className={card}>
        <div id="s2"><StepTitle n={2} done={!!file}>{t("photoOf")}</StepTitle></div>

        <div className="mt-4 grid grid-cols-2 gap-4">
          <div>
            <p className="mb-1 flex items-center gap-1.5 font-semibold text-ok"><Check className="h-5 w-5" aria-hidden="true" />{t("goodPhoto")}</p>
            <ul>
              {GOOD.map((g) => (
                <li key={g.text} className="flex items-start gap-2 py-1 text-sm text-ink">
                  <g.icon className="mt-0.5 h-5 w-5 shrink-0 text-ink-2" aria-hidden="true" />{t(g.text)}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="mb-1 flex items-center gap-1.5 font-semibold text-urgent"><X className="h-5 w-5" aria-hidden="true" />{t("avoid")}</p>
            <ul>
              {BAD.map((g) => (
                <li key={g.text} className="flex items-start gap-2 py-1 text-sm text-ink">
                  <g.icon className="mt-0.5 h-5 w-5 shrink-0 text-ink-2" aria-hidden="true" />{t(g.text)}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {preview ? (
          <div className="mt-4 flex items-center gap-4 border-t border-border pt-4">
            <img src={preview} alt={t("yourPhoto")} className="h-24 w-24 rounded-2xl object-cover ring-2 ring-brand" />
            <div>
              <p className="flex items-center gap-1.5 font-semibold text-ok"><CircleCheck className="h-5 w-5" aria-hidden="true" />{t("photoReady")}</p>
              <button type="button" className="min-h-12 font-semibold text-ink-2 underline underline-offset-4" onClick={() => { setFile(null); setPreview(null); }}>
                {t("differentPhoto")}
              </button>
            </div>
          </div>
        ) : (
          <div className={`mt-4 grid grid-cols-2 gap-3 ${crop ? "" : "opacity-50"}`}>
            <label className={`flex min-h-24 cursor-pointer flex-col items-center justify-center gap-1 rounded-2xl bg-brand text-on-brand ${crop ? "shadow-glow hover:brightness-110" : "pointer-events-none"}`}>
              <Camera className="h-8 w-8" aria-hidden="true" />
              <span className="font-semibold">{t("takePhoto")}</span>
              <input type="file" accept="image/*" capture="environment" className="sr-only" disabled={!crop}
                onChange={(e) => pick(e.target.files?.[0])} />
            </label>
            <label className={`flex min-h-24 cursor-pointer flex-col items-center justify-center gap-1 rounded-2xl border-2 border-border text-ink ${crop ? "hover:bg-surface-2" : "pointer-events-none"}`}>
              <ImageIcon className="h-8 w-8" aria-hidden="true" />
              <span className="font-semibold">{t("gallery")}</span>
              <input type="file" accept="image/*" className="sr-only" disabled={!crop}
                onChange={(e) => pick(e.target.files?.[0])} />
            </label>
          </div>
        )}
        {!crop && <p className="mt-3 flex items-center gap-2 text-sm font-semibold text-ink-2"><Info className="h-5 w-5 shrink-0" aria-hidden="true" />{t("cropFirst")}</p>}
      </section>

      <section aria-labelledby="s3" className={card}>
        <div id="s3"><StepTitle n={3} done={false}>{t("yourLanguage")}</StepTitle></div>
        <div className="mt-4 flex flex-wrap gap-2" role="radiogroup" aria-label="Reply language">
          {meta.languages.map((l) => (
            <button key={l} type="button" role="radio" aria-checked={language === l} onClick={() => onLanguage(l)} lang={l === "English" ? "en" : undefined}
              className={`min-h-12 rounded-xl border-2 px-4 font-semibold transition ${
                language === l ? "border-brand bg-brand text-on-brand" : "border-border bg-surface text-ink hover:border-ink-3"}`}>
              {NATIVE[l] ?? l}
            </button>
          ))}
        </div>
        {!meta.llm_enabled && language !== "English" && (
          <p className="mt-2 text-sm text-ink-3">{t("aiOff")}</p>
        )}
        {error && (
          <div role="alert" className="mt-4 rounded-xl bg-urgent-soft p-3 text-urgent">
            <p>{t(error)}</p>
            {(lastSample || file) && (
              <button type="button" onClick={retry}
                className="mt-2 flex min-h-12 items-center gap-2 rounded-xl bg-brand px-5 font-semibold text-on-brand">
                <RotateCcw className="h-5 w-5" aria-hidden="true" />{t("retry")}
              </button>
            )}
          </div>
        )}
        <button type="button" disabled={!crop || !file} onClick={() => submit()}
          className="mt-5 flex min-h-14 w-full items-center justify-center gap-2 rounded-2xl bg-brand text-lg font-semibold text-on-brand transition enabled:shadow-glow enabled:hover:brightness-110 disabled:opacity-40">
          <ScanSearch className="h-6 w-6" aria-hidden="true" /> {t("checkThis")}
        </button>
      </section>

      <details ref={samplesRef} className={`group ${card}`}>
        <summary className="flex min-h-12 cursor-pointer list-none items-center gap-3 font-semibold text-ink">
          <ImageIcon className="h-6 w-6 shrink-0 text-ink-2" aria-hidden="true" />
          <span className="flex-1">{t("noPlant")}</span>
          <ChevronDown className="h-5 w-5 text-ink-3 transition group-open:rotate-180" aria-hidden="true" />
        </summary>
        <p className="mt-2 text-sm text-ink-3">{t("samplesNote")}</p>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {meta.samples.map((s) => (
            <button key={s.file} type="button" onClick={() => submit(s)}
              className="overflow-hidden rounded-2xl border border-border bg-surface text-left transition hover:-translate-y-0.5 hover:border-brand hover:shadow-card">
              <img src={`${API_URL}/api/samples/${s.file}`} alt="" loading="lazy" className="aspect-square w-full object-cover" />
              <span className="flex items-start gap-1.5 p-2 text-sm font-semibold text-ink">
                <span aria-hidden="true">{CROPS[s.crop]?.emoji}</span>{t.server(s.title)}
              </span>
            </button>
          ))}
        </div>
      </details>
    </div>
  );
}
