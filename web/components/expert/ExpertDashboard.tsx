"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ApiError, expertKey, imageUrl, type Answered, type QueueItem, type Trust } from "@/lib/api";
import TrustChart from "./TrustChart";

type Tab = "queue" | "trust" | "answered";

function KeyGate({ onDone, error }: { onDone: () => void; error: string | null }) {
  const [key, setKey] = useState("");
  return (
    <form className="mx-auto mt-10 max-w-sm rounded-3xl border border-border bg-surface p-6"
      onSubmit={(e) => { e.preventDefault(); localStorage.setItem("cd_expert_key", key.trim()); onDone(); }}>
      <h1 className="text-2xl font-extrabold text-ink">Expert sign-in</h1>
      <p className="mt-1 text-sm text-ink-2">Enter the expert key set on the server (EXPERT_KEY).</p>
      <label htmlFor="key" className="mt-4 block text-sm font-semibold text-ink-2">Expert key</label>
      <input id="key" type="password" value={key} onChange={(e) => setKey(e.target.value)} autoComplete="current-password"
        className="mt-1 w-full rounded-xl border border-border px-3 py-3" />
      {error && <p role="alert" className="mt-2 text-sm text-red">{error}</p>}
      <button className="mt-4 w-full rounded-2xl bg-brand py-3 font-bold text-brand-ink">Open dashboard</button>
    </form>
  );
}

function QueueCard({ item, onAnswered }: { item: QueueItem; onAnswered: (msg: string) => void }) {
  const [label, setLabel] = useState(item.model_guess?.label ?? item.options[0]?.label ?? "");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const extra = ["Other disease / not in the list", "Photo unusable"];
  const send = async () => {
    setBusy(true);
    try {
      const r = await api.expertAnswer(item.id, label, note);
      onAnswered(r.recalibrated && r.run
        ? `Audit added: the assistant is recalibrated (coverage now ${Math.round(r.run.monitor_coverage * 100)}%).`
        : "Answer sent to the farmer and saved for retraining.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <article className="grid gap-4 rounded-3xl border border-border bg-surface p-4 sm:grid-cols-[200px_1fr]">
      <img src={imageUrl(item.image)} alt={`Leaf photo, case ${item.id}`} className="aspect-square w-full rounded-2xl object-cover" />
      <div>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="font-bold text-ink">Case #{item.id}</span>
          <span className="rounded-full bg-surface-2 px-2 py-0.5 capitalize text-ink-2">{item.crop}</span>
          <span className={`rounded-full px-2 py-0.5 font-semibold ${item.kind === "audit" ? "bg-blue-soft text-blue" : "bg-amber-soft text-amber"}`}>
            {item.kind === "audit" ? "Random audit" : "Assistant unsure"}
          </span>
        </div>
        <p className="mt-2 text-sm text-ink-2">
          {item.kind === "audit"
            ? <>The assistant answered <strong>{item.model_guess?.name}</strong>. Please check it.</>
            : <>Reason: {item.assessment.reason ?? "unsure"}.</>}
        </p>
        <ul className="mt-2 space-y-1">
          {item.assessment.top.map((t) => (
            <li key={t.label} className="flex items-center gap-2 text-sm">
              <span className="w-44 truncate text-ink">{t.name}</span>
              <span className="h-1.5 flex-1 rounded-full bg-surface-2"><span className="block h-full rounded-full bg-leaf" style={{ width: `${t.probability * 100}%` }} /></span>
              <span className="w-10 text-right text-ink-3">{Math.round(t.probability * 100)}%</span>
            </li>
          ))}
        </ul>
        {item.farmer_said.length > 0 && <p className="mt-2 text-sm text-ink-2">Farmer said: <em>{item.farmer_said.join(" · ")}</em></p>}
        <fieldset className="mt-3">
          <legend className="text-sm font-semibold text-ink-2">Your diagnosis</legend>
          <div className="mt-1 flex flex-wrap gap-2">
            {[...item.options.map((o) => ({ value: o.label, text: o.name })), ...extra.map((e) => ({ value: e, text: e }))].map((o) => (
              <button type="button" key={o.value} onClick={() => setLabel(o.value)} aria-pressed={label === o.value}
                className={`rounded-full border px-3 py-1.5 text-sm font-semibold ${label === o.value ? "border-brand bg-brand text-brand-ink" : "border-border text-ink hover:border-ink-3"}`}>
                {o.text}
              </button>
            ))}
          </div>
        </fieldset>
        <label htmlFor={`note${item.id}`} className="mt-3 block text-sm font-semibold text-ink-2">Advice for the farmer</label>
        <textarea id={`note${item.id}`} value={note} onChange={(e) => setNote(e.target.value)} rows={2}
          placeholder="e.g. Remove the lower leaves and spray copper this week. Check again in 5 days."
          className="mt-1 w-full rounded-xl border border-border p-3 text-sm" />
        <button type="button" disabled={busy || !label} onClick={send}
          className="mt-2 rounded-2xl bg-brand px-5 py-2.5 font-bold text-brand-ink disabled:opacity-50">
          Send answer to farmer
        </button>
      </div>
    </article>
  );
}

export default function ExpertDashboard() {
  const [tab, setTab] = useState<Tab>("queue");
  const [queue, setQueue] = useState<QueueItem[] | null>(null);
  const [trust, setTrust] = useState<Trust | null>(null);
  const [answered, setAnswered] = useState<Answered | null>(null);
  const [needKey, setNeedKey] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const handle = (e: unknown) => {
    if (e instanceof ApiError && e.status === 401) {
      setNeedKey(true);
      setError(expertKey() ? "That key didn't work." : null);
    } else setError(e instanceof ApiError ? e.message : "Something went wrong.");
  };

  const refresh = useCallback(async () => {
    try {
      const [q, t, a] = await Promise.all([api.queue(), api.trust(), api.answered()]);
      setQueue(q);
      setTrust(t);
      setAnswered(a);
      setNeedKey(false);
      setError(null);
    } catch (e) {
      handle(e);
    }
  }, []);

  useEffect(() => {
    const first = setTimeout(refresh, 0);           // load right away, then every 20 s
    const t = setInterval(refresh, 20000);
    return () => {
      clearTimeout(first);
      clearInterval(t);
    };
  }, [refresh]);

  const calibrate = async (action: "reset_lab" | "reset_field" | "simulate") => {
    setBusy(true);
    try {
      setTrust(await api.calibration(action, 10));
    } catch (e) {
      handle(e);
    } finally {
      setBusy(false);
    }
  };

  if (needKey) return <KeyGate error={error} onDone={refresh} />;
  const cur = trust?.current;
  const tabs: { id: Tab; label: string }[] = [
    { id: "queue", label: `Queue${queue ? ` (${queue.length})` : ""}` },
    { id: "trust", label: "Trust meter" },
    { id: "answered", label: "Answered" },
  ];

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-extrabold tracking-tight text-ink">Expert dashboard</h1>
          <p className="text-ink-2">Answer unclear photos, check random audits, and watch how trustworthy the assistant is.</p>
        </div>
        <button type="button" onClick={() => { localStorage.removeItem("cd_expert_key"); setNeedKey(true); }}
          className="text-sm font-semibold text-ink-3 underline">Sign out</button>
      </div>

      <div role="tablist" aria-label="Dashboard sections" className="mt-5 flex gap-1 rounded-2xl bg-surface-2 p-1">
        {tabs.map((t) => (
          <button key={t.id} role="tab" aria-selected={tab === t.id} onClick={() => setTab(t.id)}
            className={`flex-1 rounded-xl px-3 py-2 text-sm font-bold ${tab === t.id ? "bg-surface text-ink shadow-sm" : "text-ink-2"}`}>
            {t.label}
          </button>
        ))}
      </div>

      {toast && <p role="status" className="mt-4 rounded-xl bg-brand-soft px-4 py-3 text-sm font-semibold text-brand">{toast}</p>}
      {error && <p role="alert" className="mt-4 rounded-xl bg-red-soft px-4 py-3 text-sm text-red">{error}</p>}

      {tab === "queue" && (
        <section className="mt-5 space-y-4">
          {!queue && <p className="text-ink-3">Loading…</p>}
          {queue?.length === 0 && (
            <p className="rounded-3xl border border-dashed border-border p-8 text-center text-ink-2">
              No photos waiting. Unclear photos from farmers (and random audits) will appear here.
            </p>
          )}
          {queue?.map((q) => (
            <QueueCard key={q.id} item={q} onAnswered={(m) => { setToast(m); refresh(); }} />
          ))}
        </section>
      )}

      {tab === "trust" && cur && trust && (
        <section className="mt-5 space-y-5">
          <p className="max-w-3xl text-ink-2">
            Each random-audit answer from an expert <strong>recalibrates the assistant immediately</strong>. The model itself
            is retrained separately. Numbers below are measured on a fixed set of farm photos that are never used for fitting.
          </p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {[
              ["Field labels used", String(cur.n_field_points)],
              ["Shortlist has right disease", `${Math.round(cur.monitor_coverage * 100)}%`],
              ["Avg. shortlist length", cur.monitor_set_size.toFixed(1)],
              ["Answered without expert", `${Math.round(cur.monitor_answered * 100)}%`],
            ].map(([l, v]) => (
              <div key={l} className="rounded-2xl border border-border bg-surface p-4">
                <div className="text-2xl font-extrabold text-ink">{v}</div>
                <div className="text-sm text-ink-2">{l}</div>
              </div>
            ))}
          </div>
          {cur.n_field_points === 0 && (
            <p className="rounded-xl bg-red-soft px-4 py-3 text-sm text-red">Calibrated on lab photos only: the 90% promise isn&apos;t valid for farm photos.</p>
          )}
          {cur.n_field_points > 0 && cur.n_field_points < 9 && (
            <p className="rounded-xl bg-amber-soft px-4 py-3 text-sm text-amber">Fewer than 9 field labels: no safe threshold yet, so every disease stays possible.</p>
          )}
          <div className="rounded-3xl border border-border bg-surface p-4">
            <h2 className="font-bold text-ink">Since the last reset</h2>
            <TrustChart runs={trust.since_reset} />
          </div>
          <div className="rounded-3xl border border-border bg-surface p-4">
            <h2 className="font-bold text-ink">Demo: replay the experiment live</h2>
            <p className="text-sm text-ink-2">Start from lab-only calibration, then add expert-labelled field photos and watch the promise come back.</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button disabled={busy} onClick={() => calibrate("reset_lab")} className="rounded-2xl border border-border px-4 py-2.5 font-semibold disabled:opacity-50">Reset: lab photos only</button>
              <button disabled={busy} onClick={() => calibrate("simulate")} className="rounded-2xl bg-brand px-4 py-2.5 font-bold text-brand-ink disabled:opacity-50">+ 10 expert labels</button>
              <button disabled={busy} onClick={() => calibrate("reset_field")} className="rounded-2xl border border-border px-4 py-2.5 font-semibold disabled:opacity-50">Reset: normal calibration</button>
            </div>
          </div>
        </section>
      )}

      {tab === "answered" && answered && (
        <section className="mt-5 space-y-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-border bg-surface p-4"><div className="text-2xl font-extrabold">{answered.retraining_pool}</div><div className="text-sm text-ink-2">Labels for the next retraining</div></div>
            <div className="rounded-2xl border border-border bg-surface p-4"><div className="text-2xl font-extrabold">{answered.audits}</div><div className="text-sm text-ink-2">Random audits checked</div></div>
            <div className="rounded-2xl border border-border bg-surface p-4"><div className="text-2xl font-extrabold">{answered.audit_accuracy == null ? "–" : `${Math.round(answered.audit_accuracy * 100)}%`}</div><div className="text-sm text-ink-2">Assistant right on audits (unbiased)</div></div>
          </div>
          <div className="overflow-x-auto rounded-3xl border border-border bg-surface">
            <table className="w-full text-left text-sm">
              <thead className="bg-surface-2 text-ink-2"><tr><th className="p-3">Case</th><th className="p-3">Crop</th><th className="p-3">Assistant said</th><th className="p-3">Expert said</th><th className="p-3">Audit</th></tr></thead>
              <tbody>
                {answered.cases.map((r) => (
                  <tr key={r.id} className="border-t border-border">
                    <td className="p-3 font-semibold">#{r.id}</td><td className="p-3 capitalize">{r.crop}</td>
                    <td className="p-3">{r.assistant?.name ?? <span className="text-ink-3">sent to expert</span>}</td>
                    <td className="p-3">{r.expert?.name}{r.assistant && <span className={`ml-2 text-xs font-bold ${r.agree ? "text-brand" : "text-red"}`}>{r.agree ? "✓ agree" : "✗ differs"}</span>}</td>
                    <td className="p-3">{r.audit ? "yes" : ""}</td>
                  </tr>
                ))}
                {answered.cases.length === 0 && <tr><td colSpan={5} className="p-6 text-center text-ink-3">No expert answers yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
