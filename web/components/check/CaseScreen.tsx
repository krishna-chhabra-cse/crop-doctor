"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, imageUrl, type CaseView, type Meta, type Message } from "@/lib/api";

const URGENCY = {
  urgent: { box: "bg-red-soft text-red border-red/30", word: "Urgent" },
  soon: { box: "bg-amber-soft text-amber border-amber/30", word: "Soon" },
  routine: { box: "bg-blue-soft text-blue border-blue/30", word: "Routine" },
} as const;

// Tiny safe formatter: **bold** and line breaks only (no HTML from the server is ever injected).
function Rich({ text }: { text: string }) {
  return (
    <>
      {text.split("\n").map((line, i) => (
        <p key={i} className={i ? "mt-2" : ""}>
          {line.split(/(\*\*[^*]+\*\*)/g).map((part, j) =>
            part.startsWith("**") && part.endsWith("**") ? <strong key={j}>{part.slice(2, -2)}</strong> : part)}
        </p>
      ))}
    </>
  );
}

function Bubble({ m }: { m: Message }) {
  const mine = m.role === "farmer";
  return (
    <div className={`flex ${mine ? "justify-end" : "justify-start"}`}>
      <div className={`max-w-[85%] rounded-3xl px-4 py-3 text-[15px] leading-relaxed ${
        mine ? "rounded-br-md bg-brand text-brand-ink"
          : m.role === "expert" ? "rounded-bl-md border-2 border-leaf bg-brand-soft text-ink"
          : "rounded-bl-md border border-border bg-surface text-ink"}`}>
        {m.role === "expert" && <p className="mb-1 text-xs font-bold uppercase tracking-wide text-brand">Expert answer</p>}
        {m.image ? (
          <img src={imageUrl(m.image)} alt="Your leaf photo" className="h-44 w-44 rounded-2xl object-cover" />
        ) : (
          <Rich text={m.text} />
        )}
        {m.sources.length > 0 && (
          <details className="mt-2 text-sm">
            <summary className="cursor-pointer font-semibold text-brand">Sources ({m.sources.length})</summary>
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

function ResultCard({ c }: { c: CaseView }) {
  const a = c.assessment;
  if (a.status === "retake")
    return (
      <div className="rounded-3xl border border-amber/30 bg-amber-soft p-5 text-amber">
        <p className="text-lg font-bold">Please take a new photo</p>
        <p className="mt-1">{a.message}</p>
      </div>
    );
  if (c.status === "expert_answered" && c.expert)
    return (
      <div className="rounded-3xl border-2 border-leaf bg-brand-soft p-5">
        <p className="text-sm font-bold uppercase tracking-wide text-brand">Checked by an expert</p>
        <p className="mt-1 text-2xl font-extrabold text-ink">{c.expert.name}</p>
      </div>
    );
  if ((a.status === "diagnosis" || a.status === "healthy") && a.disease) {
    const u = a.urgency && a.urgency.level !== "none" ? URGENCY[a.urgency.level] : null;
    return (
      <div className="rounded-3xl border border-border bg-surface p-5">
        <p className="text-sm font-semibold text-ink-3">{a.status === "healthy" ? "Good news" : "Most likely"}</p>
        <p className="text-2xl font-extrabold leading-tight text-ink">{a.disease.name}</p>
        <div className="mt-3 flex items-center gap-3">
          <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-surface-2" aria-hidden="true">
            <div className="h-full rounded-full bg-brand" style={{ width: `${Math.round((a.probability ?? 0) * 100)}%` }} />
          </div>
          <span className="text-sm font-semibold text-ink-2">{Math.round((a.probability ?? 0) * 100)}% likely</span>
        </div>
        {u && a.urgency && (
          <div className={`mt-4 rounded-2xl border px-4 py-3 ${u.box}`}>
            <p className="font-bold">{u.word}: act within {a.urgency.act_within}</p>
            <p className="text-sm">{a.urgency.why}</p>
          </div>
        )}
        {a.severity_estimate?.fraction != null && (
          <p className="mt-3 text-sm text-ink-3">
            About {Math.round(a.severity_estimate.fraction * 100)}% of the leaf looks damaged (rough estimate from colour).
          </p>
        )}
        {a.status === "diagnosis" && (
          <p className="mt-2 text-sm text-ink-3">Not certain. Please confirm with a local expert before spraying.</p>
        )}
        {c.audit && c.status !== "expert_answered" && (
          <p className="mt-3 rounded-xl bg-blue-soft px-3 py-2 text-sm text-blue">An expert will also double-check this answer.</p>
        )}
      </div>
    );
  }
  return (
    <div className="rounded-3xl border border-border bg-surface p-5">
      <p className="text-sm font-semibold text-ink-3">{a.status === "question" ? "Could be one of these" : "Not sure yet"}</p>
      {a.shortlist.length > 0 ? (
        <ul className="mt-2 space-y-2">
          {a.top.filter((t) => a.shortlist.some((s) => s.label === t.label)).map((t) => (
            <li key={t.label}>
              <div className="flex justify-between text-sm font-semibold text-ink"><span>{t.name}</span><span>{Math.round(t.probability * 100)}%</span></div>
              <div className="mt-1 h-2 overflow-hidden rounded-full bg-surface-2" aria-hidden="true">
                <div className="h-full rounded-full bg-leaf" style={{ width: `${Math.round(t.probability * 100)}%` }} />
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="mt-1 text-ink-2">This photo doesn&apos;t look like the diseases the assistant knows well.</p>
      )}
      {c.status === "pending" && (
        <div className="mt-4 flex items-center gap-3 rounded-2xl bg-blue-soft px-4 py-3 text-blue" role="status">
          <span className="dot-pulse text-lg" aria-hidden="true"><span>●</span><span>●</span><span>●</span></span>
          <p className="text-sm font-semibold">Sent to an expert. Their answer will appear here; you can close this page and come back.</p>
        </div>
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
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-extrabold text-ink">Your {c.crop} leaf</h1>
        <button type="button" onClick={onNew} className="rounded-full border border-border bg-surface px-4 py-2 text-sm font-semibold text-ink hover:bg-surface-2">
          + New photo
        </button>
      </div>

      <ResultCard c={c} />

      {a.status === "question" && a.question && c.status !== "expert_answered" && (
        <section aria-labelledby="q" className="rounded-3xl border-2 border-leaf bg-surface p-5">
          <h2 id="q" className="font-bold text-ink">{a.question.text}</h2>
          <div className="mt-3 space-y-2">
            {a.question.options.map((o, i) => (
              <button key={o} type="button" disabled={busy} onClick={() => act(() => api.answerQuestion(c.id, i, language))}
                className="w-full rounded-2xl border border-border bg-surface px-4 py-3 text-left font-semibold text-ink hover:border-brand hover:bg-brand-soft disabled:opacity-50">
                {o}
              </button>
            ))}
            <button type="button" disabled={busy} onClick={() => act(() => api.answerQuestion(c.id, null, language))}
              className="w-full rounded-2xl px-4 py-3 text-left font-semibold text-ink-2 underline disabled:opacity-50">
              I&apos;m not sure: ask an expert
            </button>
          </div>
        </section>
      )}

      {c.ask_extent && c.status !== "expert_answered" && (
        <section aria-labelledby="ext" className="rounded-3xl border border-border bg-surface p-5">
          <h2 id="ext" className="font-bold text-ink">{meta.extent_question.text}</h2>
          <p className="text-sm text-ink-3">This tells us how quickly you need to act.</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-3">
            {meta.extent_question.options.map((o) => (
              <button key={o.value} type="button" disabled={busy} onClick={() => act(() => api.answerExtent(c.id, o.value))}
                className="rounded-2xl border border-border px-3 py-3 font-semibold text-ink hover:border-brand hover:bg-brand-soft disabled:opacity-50">
                {o.text}
              </button>
            ))}
          </div>
        </section>
      )}

      {a.status === "retake" && (
        <button type="button" onClick={onNew} className="w-full rounded-2xl bg-brand py-4 text-lg font-bold text-brand-ink">
          Take a new photo
        </button>
      )}

      <section aria-label="Conversation" className="space-y-3" aria-live="polite">
        {c.messages.map((m, i) => <Bubble key={i} m={m} />)}
        {busy && (
          <div className="flex justify-start"><div className="rounded-3xl border border-border bg-surface px-4 py-3">
            <span className="dot-pulse text-ink-3" aria-label="Writing a reply"><span>●</span> <span>●</span> <span>●</span></span>
          </div></div>
        )}
        <div ref={endRef} />
      </section>

      {error && <p role="alert" className="rounded-xl bg-red-soft p-3 text-sm text-red">{error}</p>}

      {a.status !== "retake" && (
        <form className="sticky bottom-3 flex gap-2 rounded-3xl border border-border bg-surface p-2 shadow-lg"
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
            className="rounded-2xl bg-brand px-4 py-2 font-bold text-brand-ink disabled:opacity-40">Send</button>
        </form>
      )}
    </div>
  );
}
