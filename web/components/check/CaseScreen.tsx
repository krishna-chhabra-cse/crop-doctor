"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorKey, imageUrl, type CaseView, type Meta, type Message } from "@/lib/api";
import { BookOpen, Camera, ChevronDown, CircleHelp, Focus, Hand, Hourglass, Leaf, LoaderCircle, Send, Sprout, Sun, UserRound } from "lucide-react";
import {
  ActionList, actionSteps, ConfidenceDots, DiseaseFacts, ExtentIcon, hasFacts, LeafDamage, ListenButton, optionIcon, PhotoCompare,
  ReferencePhotos, UrgencyLight, urgencyTone, VerdictBand, type HeroKind, type Tone,
} from "./visuals";
import { useT, type Key, type T } from "@/lib/i18n";

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
          <p key={i} className="mt-1.5 flex gap-2"><span aria-hidden="true" className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-ink-2" /><span>{bold(line.replace(/^\s*[-*•]\s+/, ""))}</span></p>
        ) : (
          <p key={i} className={i ? "mt-2" : ""}>{bold(line)}</p>
        );
      })}
    </>
  );
}

function Bubble({ m, language }: { m: Message; language: string }) {
  const t = useT();
  const mine = m.role === "farmer";
  const expert = m.role === "expert";
  const text = t.server(m.text);     // fixed server sentences (template replies, options) in the farmer's language
  return (
    <div className={`flex items-end gap-2 ${mine ? "justify-end" : "justify-start"}`}>
      {!mine && (
        <span className={`mb-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${expert ? "bg-expert-soft text-expert" : "bg-ok-soft text-ok"}`} aria-hidden="true">
          {expert ? <UserRound className="h-5 w-5" /> : <Sprout className="h-5 w-5" />}
        </span>
      )}
      <div className={`max-w-[85%] rounded-xl px-4 py-3 leading-relaxed ${
        mine ? "rounded-br-sm bg-brand text-on-brand"
          : expert ? "rounded-bl-sm border-2 border-expert bg-expert-soft text-ink"
          : "rounded-bl-sm border border-border bg-surface text-ink"}`}>
        {expert && <p className="mb-1 text-sm font-semibold text-expert">{t("expertAnswer")}</p>}
        {m.image ? (
          <img src={imageUrl(m.image)} alt={t("yourPhoto")} className="h-40 w-40 rounded-lg object-cover" />
        ) : (
          <Rich text={text} />
        )}
        {!mine && !m.image && <ListenButton text={text} language={language} />}
        {m.sources.length > 0 && (
          <details className="mt-2 text-sm">
            <summary className="flex min-h-12 cursor-pointer items-center gap-2 font-semibold text-ok">
              <BookOpen className="h-5 w-5" aria-hidden="true" /> {t("sources")} ({m.sources.length})
            </summary>
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
  if (a.unfamiliar) return "unfamiliar";
  return "expert";
}

type Verdict = { kind: HeroKind; tone?: Tone; label?: string; main: string; sub?: string };

/** The one thing the farmer must see first, as words (used by the band and by the Listen button). */
function verdictOf(c: CaseView, t: T): Verdict {
  const a = c.assessment;
  const kind = heroKind(c);
  if (kind === "answered" && c.expert) return { kind, label: t("expertSays"), main: t.server(c.expert.name) };
  if ((kind === "diagnosis" || kind === "urgent") && a.disease) {
    const u = a.urgency;
    return {
      kind, tone: urgencyTone(u?.level), label: t("mostLikely"), main: t.server(a.disease.name),
      sub: u && u.level !== "none" && u.act_within ? t("actWithin", { t: t.server(u.act_within) }) : undefined,
    };
  }
  if (kind === "healthy" && a.disease) return { kind, label: t("goodNews"), main: t.server(a.disease.name) };
  if (kind === "expert" || kind === "unfamiliar")
    return { kind, main: t(kind === "unfamiliar" ? "unfamiliar" : "heroExpert"), sub: c.status === "pending" ? t("waitingExpert") : undefined };
  return { kind, main: t(kind === "question" ? "heroQuestion" : kind === "retake" ? "heroRetake" : "heroExpert") };
}

const TIPS = [
  { icon: Sun, text: "daylight" },
  { icon: Leaf, text: "fillPhoto" },
  { icon: Focus, text: "focus" },
] as const;

/** Leaf damage, cause, spread and signs: useful, but not the first thing to read. */
function Details({ children }: { children: React.ReactNode }) {
  const t = useT();
  return (
    <details className="group border-y border-border">
      <summary className="flex min-h-12 cursor-pointer list-none items-center justify-between gap-3 font-semibold text-ink">
        {t("details")}
        <ChevronDown className="h-5 w-5 text-ink-3 transition group-open:rotate-180" aria-hidden="true" />
      </summary>
      <div className="pb-3">{children}</div>
    </details>
  );
}

function ResultBody({ c }: { c: CaseView }) {
  const t = useT();
  const a = c.assessment;
  const photo = c.image ? imageUrl(c.image) : undefined;

  if (a.status === "retake")
    return (
      <div className="space-y-4">
        <p className="text-lg font-semibold text-soon">{t.server(a.message)}</p>
        <ul className="divide-y divide-border border-y border-border">
          {TIPS.map((tip) => (
            <li key={tip.text} className="flex min-h-14 items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-2 text-ink" aria-hidden="true"><tip.icon className="h-5 w-5" /></span>
              <span className="text-lg text-ink">{t(tip.text)}</span>
            </li>
          ))}
        </ul>
      </div>
    );

  if (c.status === "expert_answered" && c.expert)
    return (
      <div className="space-y-5">
        <PhotoCompare photo={photo} disease={c.expert} />
        {hasFacts(c.expert) && <Details><DiseaseFacts d={c.expert} /></Details>}
      </div>
    );

  if ((a.status === "diagnosis" || a.status === "healthy") && a.disease) {
    const healthy = a.status === "healthy";
    const urgent = a.urgency?.level === "urgent";
    const fraction = healthy ? null : a.severity_estimate?.fraction ?? null;
    return (
      <div className="space-y-5">
        <ConfidenceDots p={a.probability ?? 0} />
        <PhotoCompare photo={photo} disease={a.disease} />
        <ActionList steps={actionSteps(a.disease, healthy, urgent)} />
        {!healthy && a.urgency && <UrgencyLight u={a.urgency} />}
        {!healthy && (fraction != null || hasFacts(a.disease)) && (
          <Details>
            {fraction != null && <LeafDamage fraction={fraction} />}
            <DiseaseFacts d={a.disease} />
          </Details>
        )}
        {!healthy && <p className="text-sm text-ink-3">{t("notCertain")}</p>}
        {c.audit && c.status !== "expert_answered" && (
          <p className="flex items-center gap-2 text-sm font-semibold text-expert">
            <UserRound className="h-5 w-5 shrink-0" aria-hidden="true" />{t("doubleCheck")}
          </p>
        )}
      </div>
    );
  }

  // Question or expert: the photo and the shortlist (the question itself is its own section below).
  const options = a.top.filter((o) => a.shortlist.some((s) => s.label === o.label));
  return (
    <div className="space-y-5">
      <PhotoCompare photo={photo} disease={null} />
      {a.unfamiliar && <p className="leading-relaxed text-ink-2">{t("unfamiliarT")}</p>}
      {a.status !== "question" && (options.length > 0 ? (
        <div>
          <p className="font-semibold text-ink">{t("couldBe")}</p>
          <ul className="mt-1 divide-y divide-border">
            {options.map((o) => (
              <li key={o.label} className="py-3">
                <p className="font-semibold text-ink">{t.server(o.name)}</p>
                <div className="mt-1"><ConfidenceDots p={o.probability} /></div>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <p className="text-ink-2">{t("unknownPhoto")}</p>
      ))}
      {c.status === "pending" && (
        <div className="flex items-start gap-3 rounded-xl bg-expert-soft px-4 py-3 text-expert" role="status">
          <Hourglass className="mt-0.5 h-6 w-6 shrink-0" aria-hidden="true" />
          <div>
            <p className="font-semibold">{t("waitingExpert")}</p>
            <p className="text-ink-2">{t("waitingNote")}</p>
          </div>
        </div>
      )}
      {c.status === "pending" && (
        <p className="flex items-start gap-2 leading-relaxed text-ink-2">
          <Hand className="mt-1 h-5 w-5 shrink-0" aria-hidden="true" />{t("waitSpray")}
        </p>
      )}
    </div>
  );
}

/** Everything the big Listen button reads: the verdict, then what to do. */
function spokenSummary(c: CaseView, v: Verdict, t: T): string {
  const a = c.assessment;
  const parts = [v.label, v.main, v.sub].filter(Boolean) as string[];
  if ((a.status === "diagnosis" || a.status === "healthy") && a.disease && c.status !== "expert_answered") {
    const healthy = a.status === "healthy";
    parts.push(t("whatToDo"), ...actionSteps(a.disease, healthy, a.urgency?.level === "urgent").map((s, i) => `${i + 1}. ${t(s.text)}`));
    if (!healthy && a.urgency?.why) parts.push(t.server(a.urgency.why));
    if (!healthy) parts.push(t("notCertain"));
  } else if (a.status === "retake") {
    parts.push(t.server(a.message), ...TIPS.map((tip) => t(tip.text)));
  } else if (a.status === "question" && a.question && c.status !== "expert_answered") {
    parts.push(t.server(a.question.text), ...a.question.options.map((o) => t.server(o)));
  } else if (c.status === "pending") {
    parts.push(t("waitingNote"), t("waitSpray"));
  }
  // A full stop after each part so the voice pauses between them.
  return parts.map((p) => (/[.।?!]$/.test(p.trim()) ? p.trim() : `${p.trim()}.`)).join(" ");
}

type Props = { id: number; meta: Meta; language: string; initial: CaseView | null; onNew: () => void };

export default function CaseScreen({ id, meta, language, initial, onNew }: Props) {
  const [c, setC] = useState<CaseView | null>(initial);
  const [busy, setBusy] = useState(false);
  const busyRef = useRef(false);
  const [error, setError] = useState<Key | null>(null);
  const [text, setText] = useState("");
  const t = useT();
  const endRef = useRef<HTMLDivElement>(null);

  // Background check for the expert's answer. A failed poll is ignored (the next one retries), and a poll that
  // lands while the farmer's own action is running must not overwrite that action's newer result.
  const load = useCallback(async () => {
    try {
      const v = await api.getCase(id);
      if (!busyRef.current) setC(v);
    } catch {}
  }, [id]);

  useEffect(() => {
    if (initial) return;
    let alive = true;
    api.getCase(id)
      .then((v) => alive && setC(v))
      .catch((e) => alive && setError(errorKey(e, "case")));
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

  const act = async (fn: () => Promise<CaseView>, onFail?: () => void) => {
    busyRef.current = true;
    setBusy(true);
    setError(null);
    try {
      setC(await fn());
    } catch (e) {
      setError(errorKey(e));
      onFail?.();
    } finally {
      busyRef.current = false;
      setBusy(false);
    }
  };

  if (!c) return error ? <p role="alert" className="rounded-xl bg-urgent-soft p-4 text-urgent">{t(error)}</p>
    : <p className="py-10 text-center text-ink-3">{t("loadingCase")}</p>;
  const a = c.assessment;
  const verdict = verdictOf(c, t);
  // The verdict is built from screen text (English or Hindi), so read it in that language.
  const screenLanguage = t.hi ? "Hindi" : "English";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3">
        <h1 className="sr-only">Your {c.crop} leaf</h1>
        <p className="text-sm font-semibold text-ink-3">{t("checkNo")} #{c.id}</p>
        <button type="button" onClick={onNew} className="flex min-h-12 items-center gap-2 rounded-xl border border-border bg-surface px-4 font-semibold text-ink hover:bg-surface-2">
          <Camera className="h-5 w-5" aria-hidden="true" /> {t("newPhoto")}
        </button>
      </div>

      <div className="space-y-3">
        <VerdictBand {...verdict} />
        <ListenButton big text={spokenSummary(c, verdict, t)} language={screenLanguage} />
      </div>

      {a.status === "question" && a.question && c.status !== "expert_answered" && (
        <section aria-labelledby="q" className="rounded-xl border-2 border-ask bg-surface p-4">
          <p className="flex items-center gap-2 text-sm font-semibold text-ask">
            <CircleHelp className="h-5 w-5" aria-hidden="true" />{t("lookClosely")}
          </p>
          <div className="mb-4 mt-3"><ReferencePhotos diseases={a.shortlist} /></div>
          <h2 id="q" className="text-lg font-semibold leading-snug text-ink">{t.server(a.question.text)}</h2>
          <div className="mt-3 grid gap-2">
            {a.question.options.map((o, i) => {
              const Icon = optionIcon(o);
              return (
                <button key={o} type="button" disabled={busy} onClick={() => act(() => api.answerQuestion(c.id, i, language))}
                  className="flex min-h-16 w-full items-center gap-3 rounded-xl border-2 border-border bg-surface px-3 py-2 text-left font-semibold text-ink transition hover:border-ask hover:bg-ask-soft disabled:opacity-50">
                  <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-surface-2 text-ink" aria-hidden="true"><Icon className="h-6 w-6" /></span>
                  <span className="leading-snug">{t.server(o)}</span>
                </button>
              );
            })}
            <button type="button" disabled={busy} onClick={() => act(() => api.answerQuestion(c.id, null, language))}
              className="flex min-h-16 w-full items-center gap-3 rounded-xl px-3 py-2 text-left font-semibold text-ink-2 hover:bg-surface-2 disabled:opacity-50">
              <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-expert-soft text-expert" aria-hidden="true"><UserRound className="h-6 w-6" /></span>
              {t("notSureExpert")}
            </button>
          </div>
        </section>
      )}

      <ResultBody c={c} />

      {c.ask_extent && c.status !== "expert_answered" && (
        <section aria-labelledby="ext" className="rounded-xl border-2 border-ask bg-surface p-4">
          <h2 id="ext" className="text-lg font-semibold leading-snug text-ink">{t.server(meta.extent_question.text)}</h2>
          <p className="text-sm text-ink-3">{t("extentWhy")}</p>
          <div className="mt-3 grid grid-cols-3 gap-2">
            {meta.extent_question.options.map((o) => (
              <button key={o.value} type="button" disabled={busy} onClick={() => act(() => api.answerExtent(c.id, o.value))}
                className="flex min-h-24 flex-col items-center justify-center gap-1 rounded-xl border-2 border-border px-2 py-3 text-center text-sm font-semibold leading-snug text-ink transition hover:border-ask hover:bg-ask-soft disabled:opacity-50">
                <ExtentIcon value={o.value} />
                {t.server(o.text)}
              </button>
            ))}
          </div>
        </section>
      )}

      {a.status === "retake" && (
        <button type="button" onClick={onNew} className="flex min-h-14 w-full items-center justify-center gap-2 rounded-xl bg-brand text-lg font-semibold text-on-brand hover:opacity-90">
          <Camera className="h-6 w-6" aria-hidden="true" /> {t("takeNew")}
        </button>
      )}

      <section aria-label="Conversation" className="space-y-3 border-t border-border pt-5" aria-live="polite">
        <h2 className="text-lg font-semibold text-ink">{t("chat")}</h2>
        {c.messages.map((m, i) => <Bubble key={i} m={m} language={language} />)}
        {busy && (
          <div className="flex justify-start"><div className="rounded-xl border border-border bg-surface px-4 py-3">
            <span className="dot-pulse text-ink-3" aria-label={t("writing")}><span>●</span> <span>●</span> <span>●</span></span>
          </div></div>
        )}
        <div ref={endRef} />
      </section>

      {error && <p role="alert" className="rounded-xl bg-urgent-soft p-3 text-urgent">{t(error)}</p>}

      {busy && (
        <div role="status" className="sticky bottom-24 z-10 mx-auto flex w-fit items-center gap-2 rounded-full bg-ink px-4 py-2 text-sm font-semibold text-background">
          <LoaderCircle className="spin h-4 w-4" aria-hidden="true" /> {t("writing")}
        </div>
      )}

      {a.status !== "retake" && (
        <form className="sticky bottom-3 flex gap-2 rounded-xl border border-border bg-surface p-2 shadow-[0_4px_16px_rgb(0_0_0/0.12)]"
          onSubmit={(e) => {
            e.preventDefault();
            const q = text.trim();
            if (!q) return;
            setText("");
            // If sending fails, give the farmer their question back instead of losing it.
            act(() => api.ask(c.id, q, language), () => setText((cur) => cur || q));
          }}>
          <label htmlFor="ask" className="sr-only">{t("askPlaceholder")}</label>
          <input id="ask" value={text} onChange={(e) => setText(e.target.value)} maxLength={1000}
            placeholder={t("askPlaceholder")}
            className="min-h-12 min-w-0 flex-1 rounded-lg bg-transparent px-3 text-ink outline-none placeholder:text-ink-3" />
          <button type="submit" disabled={busy || !text.trim()}
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-brand text-on-brand disabled:opacity-40" aria-label={t("send")}>
            <Send className="h-5 w-5" aria-hidden="true" />
          </button>
        </form>
      )}
    </div>
  );
}
