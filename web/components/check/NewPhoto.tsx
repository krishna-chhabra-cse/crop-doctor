"use client";

import { useEffect, useRef, useState } from "react";
import { api, ApiError, API_URL, type CaseView, type Meta } from "@/lib/api";

const CROPS: Record<string, { label: string; local: string; emoji: string }> = {
  tomato: { label: "Tomato", local: "टमाटर", emoji: "🍅" },
  potato: { label: "Potato", local: "आलू", emoji: "🥔" },
};
// Languages shown in their own script, so farmers recognise their language without reading English.
const NATIVE: Record<string, string> = {
  English: "English", Hindi: "हिन्दी", Tamil: "தமிழ்", Telugu: "తెలుగు", Marathi: "मराठी",
  Kannada: "ಕನ್ನಡ", Bengali: "বাংলা", Punjabi: "ਪੰਜਾਬੀ",
};
const STEPS = [
  { icon: "🔍", text: "Checking photo quality" },
  { icon: "🍃", text: "Looking at the leaf" },
  { icon: "⚖️", text: "Weighing the possible diseases" },
  { icon: "✍️", text: "Writing your answer" },
];
const GOOD = [
  { icon: "☀️", text: "Daylight" },
  { icon: "🍃", text: "One leaf fills the photo" },
  { icon: "🎯", text: "Spots in focus" },
];
const BAD = [
  { icon: "🌫️", text: "Blurry" },
  { icon: "🌑", text: "Too dark" },
  { icon: "🔭", text: "Too far away" },
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
    <h2 className="flex items-center gap-3 text-lg font-extrabold text-ink">
      <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-sm font-bold ${done ? "bg-brand text-brand-ink" : "bg-brand-soft text-brand"}`}>
        {done ? "✓" : n}
      </span>
      {children}
    </h2>
  );
}

export default function NewPhoto({ meta, language, onLanguage, onOpened, showSamples }: Props) {
  const [crop, setCrop] = useState<string | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const samplesRef = useRef<HTMLDetailsElement>(null);

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

  const submit = async (sample?: { file: string; crop: string }) => {
    const form = new FormData();
    form.set("language", language);
    if (sample) {
      form.set("crop", sample.crop);
      form.set("sample", sample.file);
      setPreview(`${API_URL}/api/samples/${sample.file}`);
    } else {
      if (!crop || !file) return;
      form.set("crop", crop);
      form.set("file", file);
    }
    setBusy(true);
    setError(null);
    setStep(0);
    const timer = setInterval(() => setStep((s) => Math.min(s + 1, STEPS.length - 1)), 1400);
    try {
      onOpened(await api.createCase(form));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
      setBusy(false);
      if (sample) setPreview(null);
    } finally {
      clearInterval(timer);
    }
  };

  if (busy)
    return (
      <div className="pop-in py-8" role="status" aria-live="polite">
        <div className="relative mx-auto h-56 w-56 overflow-hidden rounded-3xl bg-surface-2 shadow-card">
          {preview && (
            <img src={preview} alt="Your leaf photo" className="h-full w-full object-cover" />
          )}
          <div className="scan-line absolute inset-x-0 h-1 bg-leaf shadow-[0_0_18px_6px_var(--leaf)]" aria-hidden="true" />
          <div className="absolute inset-3 rounded-2xl border-2 border-dashed border-white/70" aria-hidden="true" />
        </div>
        <ol className="mx-auto mt-8 max-w-xs space-y-3">
          {STEPS.map((s, i) => (
            <li key={s.text} className={`flex items-center gap-3 rounded-2xl px-3 py-2 transition ${
              i === step ? "bg-brand-soft text-ink" : i < step ? "text-ink" : "text-ink-3"}`}>
              <span className="text-xl" aria-hidden="true">{i < step ? "✅" : s.icon}</span>
              <span className="font-semibold">{s.text}</span>
              {i === step && <span className="dot-pulse ml-auto text-brand" aria-hidden="true"><span>●</span><span>●</span><span>●</span></span>}
            </li>
          ))}
        </ol>
      </div>
    );

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-4">
        <span className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-brand-soft text-3xl" aria-hidden="true">🩺</span>
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-ink">Check a leaf</h1>
          <p className="text-ink-2">3 steps · answer in a few seconds</p>
        </div>
      </div>

      <section aria-labelledby="s1" className="rounded-3xl border border-border bg-surface p-5 shadow-card">
        <div id="s1"><StepTitle n={1} done={!!crop}>Which crop?</StepTitle></div>
        <div className="mt-4 grid grid-cols-2 gap-3" role="radiogroup" aria-label="Crop">
          {meta.crops.map((c) => {
            const on = crop === c;
            return (
              <button key={c} type="button" role="radio" aria-checked={on} onClick={() => setCrop(c)}
                className={`relative flex flex-col items-center justify-center gap-1 rounded-3xl border-2 py-5 transition ${
                  on ? "border-brand bg-brand-soft" : "border-border bg-surface hover:border-ink-3"}`}>
                {on && <span className="absolute right-3 top-3 flex h-6 w-6 items-center justify-center rounded-full bg-brand text-xs font-bold text-brand-ink" aria-hidden="true">✓</span>}
                <span className="text-5xl" aria-hidden="true">{CROPS[c]?.emoji ?? "🌱"}</span>
                <span className="text-lg font-extrabold text-ink">{CROPS[c]?.label ?? c}</span>
                <span className="text-sm text-ink-3">{CROPS[c]?.local}</span>
              </button>
            );
          })}
        </div>
      </section>

      <section aria-labelledby="s2" className={`rounded-3xl border border-border bg-surface p-5 shadow-card transition ${crop ? "" : "opacity-60"}`}>
        <div id="s2"><StepTitle n={2} done={!!file}>Photo of one sick leaf</StepTitle></div>

        <div className="mt-4 grid grid-cols-2 gap-2">
          <div className="rounded-2xl bg-brand-soft p-3">
            <p className="mb-2 text-xs font-bold uppercase tracking-wide text-brand">✓ Good photo</p>
            <ul className="space-y-1.5">
              {GOOD.map((g) => <li key={g.text} className="flex items-center gap-2 text-sm font-semibold text-ink"><span className="text-xl" aria-hidden="true">{g.icon}</span>{g.text}</li>)}
            </ul>
          </div>
          <div className="rounded-2xl bg-red-soft p-3">
            <p className="mb-2 text-xs font-bold uppercase tracking-wide text-red">✗ Avoid</p>
            <ul className="space-y-1.5">
              {BAD.map((g) => <li key={g.text} className="flex items-center gap-2 text-sm font-semibold text-ink"><span className="text-xl" aria-hidden="true">{g.icon}</span>{g.text}</li>)}
            </ul>
          </div>
        </div>

        {preview ? (
          <div className="mt-4 flex items-center gap-4 rounded-2xl bg-surface-2 p-3">
            <img src={preview} alt="Your leaf photo" className="h-24 w-24 rounded-2xl object-cover" />
            <div>
              <p className="font-bold text-ink">✅ Photo ready</p>
              <button type="button" className="mt-1 text-sm font-semibold text-ink-2 underline" onClick={() => { setFile(null); setPreview(null); }}>
                Choose a different photo
              </button>
            </div>
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-2 gap-3">
            <label className={`flex min-h-28 cursor-pointer flex-col items-center justify-center gap-1 rounded-3xl bg-brand text-brand-ink shadow-card ${crop ? "hover:brightness-110" : "pointer-events-none"}`}>
              <span className="text-4xl" aria-hidden="true">📷</span>
              <span className="font-bold">Take photo</span>
              <input type="file" accept="image/*" capture="environment" className="sr-only" disabled={!crop}
                onChange={(e) => pick(e.target.files?.[0])} />
            </label>
            <label className={`flex min-h-28 cursor-pointer flex-col items-center justify-center gap-1 rounded-3xl border-2 border-border text-ink ${crop ? "hover:bg-surface-2" : "pointer-events-none"}`}>
              <span className="text-4xl" aria-hidden="true">🖼️</span>
              <span className="font-bold">From gallery</span>
              <input type="file" accept="image/*" className="sr-only" disabled={!crop}
                onChange={(e) => pick(e.target.files?.[0])} />
            </label>
          </div>
        )}
        {!crop && <p className="mt-3 flex items-center gap-2 text-sm font-semibold text-ink-3"><span aria-hidden="true">👆</span>Choose the crop first</p>}
      </section>

      <section aria-labelledby="s3" className="rounded-3xl border border-border bg-surface p-5 shadow-card">
        <div id="s3"><StepTitle n={3} done={false}>Your language</StepTitle></div>
        <div className="mt-4 flex flex-wrap gap-2" role="radiogroup" aria-label="Reply language">
          {meta.languages.map((l) => (
            <button key={l} type="button" role="radio" aria-checked={language === l} onClick={() => onLanguage(l)} lang={l === "English" ? "en" : undefined}
              className={`rounded-full border-2 px-4 py-2 font-semibold transition ${
                language === l ? "border-brand bg-brand text-brand-ink" : "border-border bg-surface text-ink hover:border-ink-3"}`}>
              {NATIVE[l] ?? l}
            </button>
          ))}
        </div>
        {!meta.llm_enabled && language !== "English" && (
          <p className="mt-2 text-sm text-ink-3">The AI assistant is off right now, so replies will be in English.</p>
        )}
        {error && <p role="alert" className="mt-3 rounded-xl bg-red-soft p-3 text-sm text-red">{error}</p>}
        <button type="button" disabled={!crop || !file} onClick={() => submit()}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-brand py-4 text-lg font-bold text-brand-ink shadow-card transition enabled:hover:brightness-110 disabled:opacity-40">
          <span aria-hidden="true">🔎</span> Check this leaf
        </button>
      </section>

      <details ref={samplesRef} className="group rounded-3xl border border-border bg-surface p-5 shadow-card">
        <summary className="flex cursor-pointer list-none items-center gap-3 font-bold text-ink">
          <span className="text-2xl" aria-hidden="true">🖼️</span>
          <span className="flex-1">No plant nearby? Try a sample photo</span>
          <span className="text-ink-3 transition group-open:rotate-180" aria-hidden="true">▾</span>
        </summary>
        <p className="mt-2 text-sm text-ink-3">Real field photos the model never saw during training, one for each kind of answer.</p>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {meta.samples.map((s) => (
            <button key={s.file} type="button" onClick={() => submit(s)}
              className="group/s overflow-hidden rounded-2xl border border-border bg-surface text-left hover:border-brand">
              <img src={`${API_URL}/api/samples/${s.file}`} alt="" loading="lazy" className="aspect-square w-full object-cover transition group-hover/s:scale-105" />
              <span className="flex items-start gap-1.5 p-2 text-sm font-semibold text-ink">
                <span aria-hidden="true">{CROPS[s.crop]?.emoji}</span>{s.title}
              </span>
            </button>
          ))}
        </div>
      </details>
    </div>
  );
}
