"use client";

import { useEffect, useRef, useState } from "react";
import { api, ApiError, API_URL, type CaseView, type Meta } from "@/lib/api";

const CROPS: Record<string, { label: string; emoji: string }> = {
  tomato: { label: "Tomato", emoji: "🍅" },
  potato: { label: "Potato", emoji: "🥔" },
};
const STEPS = ["Checking photo quality", "Looking at the leaf", "Weighing the possible diseases", "Writing your answer"];

type Props = {
  meta: Meta;
  language: string;
  onLanguage: (l: string) => void;
  onOpened: (c: CaseView) => void;
  showSamples: boolean;
};

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
    } finally {
      clearInterval(timer);
    }
  };

  if (busy)
    return (
      <div className="py-12" role="status" aria-live="polite">
        {preview && <img src={preview} alt="Your leaf photo" className="mx-auto mb-6 h-48 w-48 rounded-2xl object-cover shadow" />}
        <ol className="mx-auto max-w-xs space-y-3">
          {STEPS.map((s, i) => (
            <li key={s} className={`flex items-center gap-3 ${i <= step ? "text-ink" : "text-ink-3"}`}>
              <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                i < step ? "bg-brand text-brand-ink" : i === step ? "bg-brand-soft text-brand" : "bg-surface-2"}`}>
                {i < step ? "✓" : i + 1}
              </span>
              {s}{i === step && <span className="dot-pulse" aria-hidden="true"><span>.</span><span>.</span><span>.</span></span>}
            </li>
          ))}
        </ol>
      </div>
    );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-extrabold tracking-tight text-ink">Check a leaf</h1>
        <p className="mt-1 text-ink-2">Three quick steps. You&apos;ll get an answer in a few seconds.</p>
      </div>

      <section aria-labelledby="s1" className="rounded-3xl border border-border bg-surface p-5">
        <h2 id="s1" className="font-bold text-ink"><span className="text-brand">1.</span> Which crop is it?</h2>
        <div className="mt-3 grid grid-cols-2 gap-3" role="radiogroup" aria-label="Crop">
          {meta.crops.map((c) => (
            <button key={c} type="button" role="radio" aria-checked={crop === c} onClick={() => setCrop(c)}
              className={`flex min-h-20 items-center justify-center gap-3 rounded-2xl border-2 text-lg font-bold transition ${
                crop === c ? "border-brand bg-brand-soft text-brand" : "border-border bg-surface text-ink hover:border-ink-3"}`}>
              <span className="text-3xl" aria-hidden="true">{CROPS[c]?.emoji ?? "🌱"}</span>
              {CROPS[c]?.label ?? c}
            </button>
          ))}
        </div>
      </section>

      <section aria-labelledby="s2" className={`rounded-3xl border border-border bg-surface p-5 transition ${crop ? "" : "opacity-60"}`}>
        <h2 id="s2" className="font-bold text-ink"><span className="text-brand">2.</span> Photo of one affected leaf</h2>
        <ul className="mt-2 grid gap-1 text-sm text-ink-2 sm:grid-cols-2">
          <li>☀️ Daylight, no flash</li>
          <li>🍃 One leaf fills most of the photo</li>
          <li>✋ Hold steady, tap the leaf to focus</li>
          <li>🔄 Show the spots clearly</li>
        </ul>
        {preview ? (
          <div className="mt-4 flex items-center gap-4">
            <img src={preview} alt="Your leaf photo" className="h-28 w-28 rounded-2xl object-cover" />
            <button type="button" className="rounded-xl px-3 py-2 text-sm font-semibold text-ink-2 underline" onClick={() => { setFile(null); setPreview(null); }}>
              Choose a different photo
            </button>
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-2 gap-3">
            <label className={`flex min-h-24 cursor-pointer flex-col items-center justify-center rounded-2xl bg-brand text-brand-ink ${crop ? "hover:brightness-110" : "pointer-events-none"}`}>
              <span className="text-2xl" aria-hidden="true">📷</span>
              <span className="font-bold">Take photo</span>
              <input type="file" accept="image/*" capture="environment" className="sr-only" disabled={!crop}
                onChange={(e) => pick(e.target.files?.[0])} />
            </label>
            <label className={`flex min-h-24 cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-border text-ink ${crop ? "hover:bg-surface-2" : "pointer-events-none"}`}>
              <span className="text-2xl" aria-hidden="true">🖼️</span>
              <span className="font-bold">From gallery</span>
              <input type="file" accept="image/*" className="sr-only" disabled={!crop}
                onChange={(e) => pick(e.target.files?.[0])} />
            </label>
          </div>
        )}
        {!crop && <p className="mt-3 text-sm text-ink-3">Choose the crop first.</p>}
      </section>

      <section aria-labelledby="s3" className="rounded-3xl border border-border bg-surface p-5">
        <h2 id="s3" className="font-bold text-ink"><span className="text-brand">3.</span> Get your answer</h2>
        <label className="mt-3 block text-sm font-semibold text-ink-2" htmlFor="lang">Reply language</label>
        <select id="lang" value={language} onChange={(e) => onLanguage(e.target.value)}
          className="mt-1 w-full rounded-xl border border-border bg-surface px-3 py-3 text-ink">
          {meta.languages.map((l) => <option key={l}>{l}</option>)}
        </select>
        {!meta.llm_enabled && language !== "English" && (
          <p className="mt-2 text-sm text-ink-3">Replies in other languages need the AI assistant, which is off right now, so replies will be in English.</p>
        )}
        {error && <p role="alert" className="mt-3 rounded-xl bg-red-soft p-3 text-sm text-red">{error}</p>}
        <button type="button" disabled={!crop || !file} onClick={() => submit()}
          className="mt-4 w-full rounded-2xl bg-brand py-4 text-lg font-bold text-brand-ink shadow-sm transition enabled:hover:brightness-110 disabled:opacity-40">
          Check this leaf
        </button>
      </section>

      <details ref={samplesRef} className="rounded-3xl border border-border bg-surface p-5">
        <summary className="cursor-pointer font-bold text-ink">No plant nearby? Try a sample photo</summary>
        <p className="mt-2 text-sm text-ink-3">Real field photos the model never saw during training, one for each kind of answer.</p>
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {meta.samples.map((s) => (
            <button key={s.file} type="button" onClick={() => submit(s)}
              className="group overflow-hidden rounded-2xl border border-border text-left hover:border-brand">
              <img src={`${API_URL}/api/samples/${s.file}`} alt="" loading="lazy" className="aspect-square w-full object-cover transition group-hover:scale-105" />
              <span className="block p-2 text-sm font-semibold text-ink">{s.title}</span>
            </button>
          ))}
        </div>
      </details>
    </div>
  );
}
