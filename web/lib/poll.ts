"use client";

// Run `fn` every `ms` milliseconds, but only while the page is visible. A hidden tab (phone locked, another app
// open) stops asking the free server, which would otherwise keep it awake for nobody. When the page becomes
// visible again, `fn` runs at once, so the farmer sees an expert's answer straight away.
import { useEffect, useRef } from "react";

export function useVisiblePoll(fn: () => void, ms: number, enabled = true) {
  const latest = useRef(fn);
  useEffect(() => {
    latest.current = fn;
  }, [fn]);

  useEffect(() => {
    if (!enabled) return;
    let timer: ReturnType<typeof setInterval> | null = null;
    const start = () => {
      if (timer === null) timer = setInterval(() => latest.current(), ms);
    };
    const stop = () => {
      if (timer !== null) clearInterval(timer);
      timer = null;
    };
    const onVisibility = () => {
      if (document.hidden) stop();
      else {
        latest.current();
        start();
      }
    };
    if (!document.hidden) start();
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [ms, enabled]);
}
