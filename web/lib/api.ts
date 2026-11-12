// Typed client for the Crop Doctor API (FastAPI on Render).
// NEXT_PUBLIC_API_URL is set in Vercel; locally it defaults to the uvicorn dev server.

import type { Key } from "./i18n";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export type Disease = {
  label: string;
  name: string;
  crop: string | null;
  cause?: string | null;
  spread?: string | null;
  signs?: string | null;
};
export type Urgency = { level: "urgent" | "soon" | "routine" | "none"; act_within: string | null; why: string };
export type Assessment = {
  status: "diagnosis" | "healthy" | "question" | "expert" | "retake";
  disease: Disease | null;
  probability?: number;
  shortlist: Disease[];
  top: { label: string; name: string; probability: number }[];
  urgency?: Urgency;
  severity_estimate?: { fraction: number | null; band: string };
  question?: { id: string; text: string; options: string[] };
  reason?: string;
  message?: string;
  extent?: string | null;
  quality?: { ok: boolean; problems: string[] };
  unfamiliar?: boolean;
  familiarity?: number | null;
};
export type Message = {
  role: "farmer" | "assistant" | "expert";
  text: string;
  created_at: string;
  sources: string[];
  used_llm: boolean;
  image?: string;
};
export type CaseView = {
  id: number;
  crop: string;
  status: "answered" | "pending" | "expert_answered" | "retake";
  audit: boolean;
  created_at: string;
  image: string;
  assessment: Assessment;
  messages: Message[];
  expert: Disease | null;
  ask_extent: boolean;
};
export type Meta = {
  crops: string[];
  diseases: Disease[];
  extent_question: { text: string; options: { text: string; value: string }[] };
  samples: { file: string; title: string; crop: string }[];
  languages: string[];
  llm_enabled: boolean;
  expert_key_required: boolean;
};
export type QueueItem = CaseView & {
  farmer_said: string[];
  kind: "audit" | "unsure";
  model_guess: Disease | null;
  options: Disease[];
};
export type CalibrationRun = {
  id: number;
  created_at: string;
  n_points: number;
  n_field_points: number;
  temperature: number;
  qhat: number | null;
  monitor_coverage: number;
  monitor_set_size: number;
  monitor_answered: number;
  note: string | null;
};
export type Trust = { current: CalibrationRun | null; since_reset: CalibrationRun[]; all: CalibrationRun[] };
export type Answered = {
  cases: { id: number; crop: string; audit: boolean; assistant: Disease | null; expert: Disease | null; agree: boolean; answered_at: string }[];
  retraining_pool: number;
  audits: number;
  audit_accuracy: number | null;
};

// status 0 = no connection, -1 = timed out. `message` is the server's English detail (shown only to experts);
// farmer screens show a translated text from errorKey() instead.
export const OFFLINE = 0;
export const TIMEOUT = -1;
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

/** Translated message for a failed request. context "photo": a 400 means the upload wasn't a readable photo. */
export function errorKey(e: unknown, context: "photo" | "case" | "other" = "other"): Key {
  if (!(e instanceof ApiError)) return "errGeneric";
  const s = e.status;
  if (s === OFFLINE) return "errOffline";
  if (s === TIMEOUT) return "errTimeout";
  if (s === 413) return "errTooLarge";
  if (s === 400 && context === "photo") return "errNotPhoto";
  if (s === 429) return "errTooMany";
  if (s === 404 && context === "case") return "errNotFound";
  if (s === 409) return "errConflict";
  if (s >= 500) return "errServer";
  return "errGeneric";
}

// Long enough for the free server's cold start (30-60 s) plus a slow AI reply; after that, show a Retry.
const TIMEOUT_MS = 90_000;
const UPLOAD_TIMEOUT_MS = 120_000;   // also covers sending the photo over a slow connection

export const imageUrl = (path: string) => (path.startsWith("http") ? path : `${API_URL}${path}`);

function newId(): string {
  try {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") return crypto.randomUUID();
  } catch {}
  try {
    const b = new Uint8Array(16);
    crypto.getRandomValues(b);
    return Array.from(b, (x) => x.toString(16).padStart(2, "0")).join("");
  } catch {}
  return `${Math.random().toString(16).slice(2)}${Math.random().toString(16).slice(2)}${Date.now().toString(16)}`;
}

// The session id is what makes a farmer's cases private to this browser. If storage is blocked (private mode,
// old browsers) it still works for this visit, kept in memory.
let memorySession: string | null = null;
function sessionId(): string {
  if (typeof window === "undefined") return "server";
  if (memorySession) return memorySession;
  let id: string | null = null;
  try {
    id = localStorage.getItem("cd_session");
  } catch {}
  if (!id) {
    id = newId();
    try {
      localStorage.setItem("cd_session", id);
    } catch {}
  }
  memorySession = id;
  return id;
}

export function expertKey(): string {
  if (typeof window === "undefined") return "";
  try {
    return localStorage.getItem("cd_expert_key") ?? "";
  } catch {
    return "";
  }
}

async function request<T>(path: string, init: RequestInit = {}, expert = false): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-Session-Id", sessionId());
  if (expert) headers.set("X-Expert-Key", expertKey());
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    let res: Response;
    try {
      res = await fetch(`${API_URL}${path}`, { ...init, headers, signal: ctrl.signal });
    } catch {
      throw new ApiError(ctrl.signal.aborted ? TIMEOUT : OFFLINE, ctrl.signal.aborted ? "Timed out" : "Can't reach the server");
    }
    if (!res.ok) {
      let detail: unknown = res.statusText;
      try {
        detail = (await res.json()).detail ?? detail;
      } catch {}
      throw new ApiError(res.status, typeof detail === "string" ? detail : "Something went wrong");
    }
    try {
      return (await res.json()) as T;
    } catch {
      throw new ApiError(ctrl.signal.aborted ? TIMEOUT : OFFLINE, "The reply was cut off");
    }
  } finally {
    clearTimeout(timer);
  }
}

/** POST /api/cases with real upload progress (fetch can't report it). onProgress gets 0..1; onSent fires when
 * the photo is fully sent and the server starts checking it. */
function uploadCase(form: FormData, onProgress?: (fraction: number) => void, onSent?: () => void): Promise<CaseView> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/api/cases`);
    xhr.timeout = UPLOAD_TIMEOUT_MS;
    xhr.setRequestHeader("X-Session-Id", sessionId());
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && e.total > 0) onProgress?.(e.loaded / e.total);
    };
    xhr.upload.onload = () => onSent?.();
    xhr.onerror = () => reject(new ApiError(OFFLINE, "Can't reach the server"));
    xhr.ontimeout = () => reject(new ApiError(TIMEOUT, "Timed out"));
    xhr.onload = () => {
      let body: unknown = null;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {}
      if (xhr.status >= 200 && xhr.status < 300 && body) return resolve(body as CaseView);
      const detail = (body as { detail?: unknown } | null)?.detail;
      reject(new ApiError(xhr.status, typeof detail === "string" ? detail : xhr.statusText || "Something went wrong"));
    };
    xhr.send(form);
  });
}

export const api = {
  health: () => request<{ ok: boolean }>("/api/health"),
  meta: () => request<Meta>("/api/meta"),
  getCase: (id: number) => request<CaseView>(`/api/cases/${id}`),
  createCase: uploadCase,
  answerQuestion: (id: number, option: number | null, language: string) =>
    request<CaseView>(`/api/cases/${id}/question`, { method: "POST", body: JSON.stringify({ option, language }) }),
  answerExtent: (id: number, value: string) =>
    request<CaseView>(`/api/cases/${id}/extent`, { method: "POST", body: JSON.stringify({ value }) }),
  ask: (id: number, text: string, language: string) =>
    request<CaseView>(`/api/cases/${id}/messages`, { method: "POST", body: JSON.stringify({ text, language }) }),
  queue: () => request<QueueItem[]>("/api/expert/queue", {}, true),
  expertAnswer: (id: number, label: string, note: string) =>
    request<{ recalibrated: boolean; run: CalibrationRun | null }>(
      `/api/expert/cases/${id}`, { method: "POST", body: JSON.stringify({ label, note }) }, true),
  trust: () => request<Trust>("/api/expert/trust", {}, true),
  calibration: (action: "reset_lab" | "reset_field" | "simulate", k = 10) =>
    request<Trust>("/api/expert/calibration", { method: "POST", body: JSON.stringify({ action, k }) }, true),
  answered: () => request<Answered>("/api/expert/answered", {}, true),
};
