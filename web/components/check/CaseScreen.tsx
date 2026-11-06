"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, imageUrl, type CaseView, type Meta, type Message } from "@/lib/api";
import {
  ActionTiles, ConfidenceDots, DiseaseFacts, EXTENT_ICON, LeafDamage, ListenButton, optionIcon, StatusHero, UrgencyLight,
  type HeroKind,
} from "./visuals";

// Tiny safe formatter: **bold**, "- " bullets and line breaks only (no HTML from the server is ever injected).
function Rich({ text }: { text: string }) {
  const bold = (line: string) =>
    line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
      part.startsWith("**") && part.endsWith("**") ? <strong key={j}>{part.slice(2, -2)}</strong> : part);
  const body = text.replace(/\n*Sources:[\s\S]*$/, "");      // sources are shown separately, below
  return (
    <>
      {body.split("\n").filter((l) => l.trim()).map((line, i) => {
        const bullet = /^\s*[-*•]\s+/.test(line);
        return bullet ? (
          <p key={i} className="mt-1.5 flex gap-2"><span aria-hidden="true" className="text-brand">●</span><span>{bold(line.replace(/^\s*[-*•]\s+/, ""))}</span></p>
        ) : (
          <p key={i} className={i ? "mt-2" : ""}>{bold(line)}</p>
        );
      })}
    </>
  );
}

function Bubble({ m, language }: { m: Message; language: string }) {
  const mine = m.role === "farmer";
  return (
    <div className={`pop-in flex items-end gap-2 ${mine ? "justify-end" : "justify-start"}`}>
      {!mine && (
        <span className={`mb-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-base ${m.role === "expert" ? "bg-brand text-brand-ink" : "bg-brand-soft"}`} aria-hidden="true">
          {m.role === "expert" ? "🧑‍🌾" : "🌱"}
        </span>
      )}
      <div className={`max-w-[85%] rounded-3xl px-4 py-3 text-[15px] leading-relaxed ${
        mine ? "rounded-br-md bg-brand text-brand-ink"
          : m.role === "expert" ? "rounded-bl-md border-2 border-leaf bg-brand-soft text-ink"
          : "rounded-bl-md border border-border bg-surface text-ink shadow-card"}`}>
        {m.role === "expert" && <p className="mb-1 text-xs font-bold uppercase tracking-wide text-brand">Expert answer</p>}
        {m.image ? (
          <img src={imageUrl(m.image)} alt="Your leaf photo" className="h-40 w-40 rounded-2xl object-cover" />
        ) : (
          <Rich text={m.text} />
        )}
        {!mine && !m.image && <ListenButton text={m.text} language={language} />}
        {m.sources.length > 0 && (
          <details className="mt-2 text-sm">
            <summary className="cursor-pointer font-semibold text-brand">📚 Sources ({m.sources.length})</summary>
            <ul className="mt-1 space-y-1 text-ink-2">
              {m.sources.map((s) => {
                const url = s.match(/https?:\/\/\S+/)?.[0];
                const label = url ? s.replace(url, "").replace(/:\s*$/, "") : s;
                return <li key={s}>{url ? <a className="underline" href={url} target="_blank" rel="noreferrer">{label}</a> : label}</li>;
              })}
            </ul>
          </details>
        )}
      </div>
    </div>
  );
}

function heroKind(c: CaseView): HeroKind {
  const a = c.assessment;
  if (c.status === "expert_answered") return "answered";
  if (a.status === "retake") return "retake";
  if (a.status === "healthy") return "healthy";
  if (a.status === "diagnosis") return a.urgency?.level === "urgent" ? "urgent" : "diagnosis";
  if (a.status === "question") return "question";
  return "expert";
}

function ResultCard({ c }: { c: CaseView }) {
  const a = c.assessment;
  const kind = heroKind(c);
  const shell = "pop-in space-y-4 rounded-3xl border border-border bg-surface p-5 shadow-card";
  const hero = <StatusHero kind={kind} photo={c.image ? imageUrl(c.image) : undefined} crop={c.crop} />;

  if (a.status === "retake")
    return (
      <div className={shell}>
        {hero}
        <p className="rounded-2xl bg-amber-soft p-4 font-semibold text-amber">{a.message}</p>
        <div className="grid grid-cols-3 gap-2 text-center text-xs font-semibold text-ink-2">
          {[["☀️", "Daylight"], ["🍃", "Fill the photo"], ["✋", "Hold steady"]].map(([i, w]) => (
            <div key={w} className="rounded-2xl bg-surface-2 p-3"><div className="text-2xl" aria-hidden="true">{i}</div>{w}</div>
          ))}
        </div>
      </div>
    );

  if (c.status === "expert_answered" && c.expert)
    return (
      <div className={`${shell} border-2 border-leaf`}>
        {hero}
        <div className="rounded-2xl bg-brand-soft p-4">
          <p className="text-sm font-semibold text-brand">The expert says</p>
          <p className="text-2xl font-extrabold text-ink">{c.expert.name}</p>
        </div>
        <DiseaseFacts d={c.expert} />
      </div>
    );

  if ((a.status === "diagnosis" || a.status === "healthy") && a.disease) {
    const healthy = a.status === "healthy";
    return (
      <div className={shell}>
        {hero}
        <div>
          <p className="text-sm font-semibold text-ink-3">{healthy ? "Good news" : "Most likely"}</p>
          <p className="text-2xl font-extrabold leading-tight text-ink sm:text-3xl">{a.disease.name}</p>
          <div className="mt-2"><ConfidenceDots p={a.probability ?? 0} /></div>
        </div>
        {a.urgency && <UrgencyLight u={a.urgency} />}
        {!healthy && a.severity_estimate?.fraction != null && <LeafDamage fraction={a.severity_estimate.fraction} />}
        {!healthy && <DiseaseFacts d={a.disease} />}
        <ActionTiles d={a.disease} healthy={healthy} urgent={a.urgency?.level === "urgent"} />
        {!healthy && (
          <p className="flex items-start gap-2 rounded-2xl bg-surface-2 p-3 text-sm text-ink-2">
            <span aria-hidden="true">⚠️</span>Not 100% certain. Please confirm with a local expert before spraying.
          </p>
        )}
        {c.audit && c.status !== "expert_answered" && (
          <p className="flex items-center gap-2 rounded-2xl bg-blue-soft px-3 py-2 text-sm text-blue">
            <span aria-hidden="true">🧑‍🌾</span>An expert will also double-check this answer.
          </p>
        )}
      </div>
    );
  }

  const options = a.top.filter((t) => a.shortlist.some((s) => s.label === t.label));
  return (
    <div className={shell}>
      {hero}
      {options.length > 0 ? (
        <div>
          <p className="text-sm font-semibold text-ink-3">It could be one of these</p>
          <ul className="mt-2 space-y-3">
            {options.map((t) => (
              <li key={t.label} className="rounded-2xl bg-surface-2 p-3">
                <p className="font-bold text-ink">{t.name}</p>
                <div className="mt-1"><ConfidenceDots p={t.probability} tone="leaf" /></div>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-ink-2">This photo doesn&apos;t look like the diseases the assistant knows well.</p>
      )}
      {c.status === "pending" && (
        <div className="flex items-center gap-3 rounded-2xl bg-blue-soft px-4 py-3 text-blue" role="status">
          <span className="text-2xl" aria-hidden="true">⏳</span>
          <div>
            <p className="font-bold">Waiting for the expert</p>
            <p className="text-sm">Their answer will appear here. You can close this page and come back later.</p>
          </div>
        </div>
      )}
      {c.status === "pending" && (
        <p className="flex items-start gap-2 rounded-2xl bg-surface-2 p-3 text-sm text-ink-2">
          <span aria-hidden="true">✋</span>Wait for the expert before buying or spraying any chemical. Meanwhile, remove badly affected leaves and keep them away from the field.
        </p>
      )}
    </div>
  );
}

type Props = { id: number; meta: Meta; language: string; initial: CaseView | null; onNew: () => void };

export default function CaseScreen({ id, meta, language, initial, onNew }: Props) {
  const [c, setC] = useState<CaseView | null>(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [text, setText] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  const load = useCallback(async () => {
    try {
      setC(await api.getCase(id));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load this check.");
    }
  }, [id]);

  useEffect(() => {
    if (initial) return;
    let alive = true;
    api.getCase(id)
      .then((v) => alive && setC(v))
      .catch((e) => alive && setError(e instanceof ApiError ? e.message : "Could not load this check."));
    return () => {
      alive = false;
    };
  }, [id, initial]);

  // Waiting for an expert: check for their answer every 15 seconds.
  useEffect(() => {
    if (c?.status !== "pending" && !(c?.audit && c.status === "answered")) return;
    const t = setInterval(load, 15000);
    return () => clearInterval(t);
  }, [c?.status, c?.audit, load]);

  // Scroll to new chat messages, but not on first load: the farmer should see the result card first.
  const seen = useRef<number | null>(null);
  useEffect(() => {
    const n = c?.messages.length ?? 0;
    if (seen.current !== null && n > seen.current) endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
    if (n) seen.current = n;
  }, [c?.messages.length]);

  const act = async (fn: () => Promise<CaseView>) => {
    setBusy(true);
    setError(null);
    try {
      setC(await fn());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  if (!c) return error ? <p role="alert" className="rounded-2xl bg-red-soft p-4 text-red">{error}</p>
    : <p className="py-10 text-center text-ink-3">Loading…</p>;
  const a = c.assessment;

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3">
        <h1 className="sr-only">Your {c.crop} leaf</h1>
        <p className="text-sm font-semibold text-ink-3">Check #{c.id}</p>
        <button type="button" onClick={onNew} className="flex items-center gap-1.5 rounded-full border border-border bg-surface px-4 py-2 text-sm font-semibold text-ink shadow-card hover:bg-surface-2">
          <span aria-hidden="true">📷</span> New photo
        </button>
      </div>

      <ResultCard c={c} />

      {a.status === "question" && a.question && c.status !== "expert_answered" && (
        <section aria-labelledby="q" className="pop-in rounded-3xl border-2 border-blue/40 bg-surface p-5 shadow-card">
          <p className="text-sm font-semibold text-blue">Look closely at your leaf</p>
          <h2 id="q" className="text-lg font-extrabold text-ink">{a.question.text}</h2>
          <div className="mt-3 grid gap-2">
            {a.question.options.map((o, i) => (
              <button key={o} type="button" disabled={busy} onClick={() => act(() => api.answerQuestion(c.id, i, language))}
                className="flex w-full items-center gap-3 rounded-2xl border-2 border-border bg-surface px-4 py-3 text-left font-semibold text-ink transition hover:border-brand hover:bg-brand-soft disabled:opacity-50">
                <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-surface-2 text-2xl" aria-hidden="true">{optionIcon(o)}</span>
                <span className="leading-snug">{o}</span>
              </button>
            ))}
            <button type="button" disabled={busy} onClick={() => act(() => api.answerQuestion(c.id, null, language))}
              className="flex w-full items-center gap-3 rounded-2xl px-4 py-3 text-left font-semibold text-ink-2 hover:bg-surface-2 disabled:opacity-50">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center text-2xl" aria-hidden="true">🤷</span>
              I&apos;m not sure: ask an expert
            </button>
          </div>
        </section>
      )}

      {c.ask_extent && c.status !== "expert_answered" && (
        <section aria-labelledby="ext" className="pop-in rounded-3xl border border-border bg-surface p-5 shadow-card">
          <h2 id="ext" className="text-lg font-extrabold text-ink">{meta.extent_question.text}</h2>
          <p className="text-sm text-ink-3">This tells us how quickly you need to act.</p>
          <div className="mt-3 grid grid-cols-3 gap-2">
            {meta.extent_question.options.map((o) => (
              <button key={o.value} type="button" disabled={busy} onClick={() => act(() => api.answerExtent(c.id, o.value))}
                className="flex flex-col items-center gap-1 rounded-2xl border-2 border-border px-2 py-3 text-center text-sm font-semibold leading-snug text-ink transition hover:border-brand hover:bg-brand-soft disabled:opacity-50">
                <span className="text-4xl" aria-hidden="true">{EXTENT_ICON[o.value] ?? "🌱"}</span>
                {o.text}
              </button>
            ))}
          </div>
        </section>
      )}

      {a.status === "retake" && (
        <button type="button" onClick={onNew} className="w-full rounded-2xl bg-brand py-4 text-lg font-bold text-brand-ink shadow-card">
          📷 Take a new photo
        </button>
      )}

      <section aria-label="Conversation" className="space-y-3" aria-live="polite">
        <h2 className="pt-2 text-sm font-bold uppercase tracking-wide text-ink-3">Chat with the crop doctor</h2>
        {c.messages.map((m, i) => <Bubble key={i} m={m} language={language} />)}
        {busy && (
          <div className="flex justify-start"><div className="rounded-3xl border border-border bg-surface px-4 py-3">
            <span className="dot-pulse text-ink-3" aria-label="Writing a reply"><span>●</span> <span>●</span> <span>●</span></span>
          </div></div>
        )}
        <div ref={endRef} />
      </section>

      {error && <p role="alert" className="rounded-xl bg-red-soft p-3 text-sm text-red">{error}</p>}

      {busy && (
        <div role="status" className="pop-in sticky bottom-20 z-10 mx-auto flex w-fit items-center gap-2 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-background shadow-card">
          <span aria-hidden="true">✍️</span> Writing your answer
          <span className="dot-pulse" aria-hidden="true"><span>●</span><span>●</span><span>●</span></span>
        </div>
      )}

      {a.status !== "retake" && (
        <form className="sticky bottom-3 flex gap-2 rounded-3xl border border-border bg-surface p-2 shadow-card"
          onSubmit={(e) => {
            e.preventDefault();
            const t = text.trim();
            if (!t) return;
            setText("");
            act(() => api.ask(c.id, t, language));
          }}>
          <label htmlFor="ask" className="sr-only">Ask a question about this disease</label>
          <input id="ask" value={text} onChange={(e) => setText(e.target.value)} maxLength={1000}
            placeholder="Ask anything, e.g. can I use an organic spray?"
            className="min-w-0 flex-1 rounded-2xl bg-transparent px-3 py-2 text-ink outline-none placeholder:text-ink-3" />
          <button type="submit" disabled={busy || !text.trim()}
            className="rounded-2xl bg-brand px-5 py-2 text-lg font-bold text-brand-ink disabled:opacity-40" aria-label="Send">➤</button>
        </form>
      )}
    </div>
  );
}
