// Typed client for the Crop Doctor API (FastAPI on Render).
// NEXT_PUBLIC_API_URL is set in Vercel; locally it defaults to the uvicorn dev server.

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

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export const imageUrl = (path: string) => (path.startsWith("http") ? path : `${API_URL}${path}`);

function sessionId(): string {
  if (typeof window === "undefined") return "server";
  let id = localStorage.getItem("cd_session");
  if (!id) {
    id = crypto.randomUUID().slice(0, 12);
    localStorage.setItem("cd_session", id);
  }
  return id;
}

export function expertKey(): string {
  return typeof window === "undefined" ? "" : localStorage.getItem("cd_expert_key") ?? "";
}

async function request<T>(path: string, init: RequestInit = {}, expert = false): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("X-Session-Id", sessionId());
  if (expert) headers.set("X-Expert-Key", expertKey());
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, "Can't reach the server. Check your internet connection and try again.");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {}
    throw new ApiError(res.status, typeof detail === "string" ? detail : "Something went wrong");
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ ok: boolean }>("/api/health"),
  meta: () => request<Meta>("/api/meta"),
  getCase: (id: number) => request<CaseView>(`/api/cases/${id}`),
  createCase: (form: FormData) => request<CaseView>("/api/cases", { method: "POST", body: form }),
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
