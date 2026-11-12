"use client";

// The farmer's recent checks (case numbers, newest first), kept in this browser so they can come back to a
// case that is waiting for an expert. Storage may be blocked: then the list is simply empty.
import { useMemo, useSyncExternalStore } from "react";

const KEY = "cd_cases";
const listeners = new Set<() => void>();
const subscribe = (fn: () => void) => {
  listeners.add(fn);
  const onStorage = (e: StorageEvent) => e.key === KEY && fn();
  window.addEventListener("storage", onStorage);
  return () => {
    listeners.delete(fn);
    window.removeEventListener("storage", onStorage);
  };
};

function raw(): string {
  try {
    return localStorage.getItem(KEY) ?? "[]";
  } catch {
    return "[]";
  }
}

function parse(s: string): number[] {
  try {
    const v: unknown = JSON.parse(s);
    return Array.isArray(v) ? v.filter((x): x is number => Number.isInteger(x) && x > 0) : [];
  } catch {
    return [];
  }
}

export function rememberCase(id: number) {
  const list = [id, ...parse(raw()).filter((x) => x !== id)].slice(0, 10);
  try {
    localStorage.setItem(KEY, JSON.stringify(list));
  } catch {}
  listeners.forEach((fn) => fn());
}

export function useRecentCases(): number[] {
  const s = useSyncExternalStore(subscribe, raw, () => "[]");
  return useMemo(() => parse(s), [s]);
}
