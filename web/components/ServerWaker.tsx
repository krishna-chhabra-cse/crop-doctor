"use client";

// The backend sleeps after 15 minutes without visitors and takes about a minute to start again. We ping it as
// soon as anyone opens the site, and tell them (in their language) if it's starting or if they're offline.
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { api } from "@/lib/api";
import { useT } from "@/lib/i18n";

type State = "checking" | "slow" | "offline" | "ok" | "down";

export default function ServerWaker() {
  const [state, setState] = useState<State>("checking");
  const t = useT();
  const pathname = usePathname();

  useEffect(() => {
    let done = false;
    const slow = setTimeout(() => !done && setState((s) => (s === "checking" ? "slow" : s)), 2500);
    const tryHealth = async (attempt: number): Promise<void> => {
      try {
        await api.health();
        done = true;
        setState("ok");
      } catch {
        if (done) return;
        const offline = typeof navigator !== "undefined" && navigator.onLine === false;
        setState(offline ? "offline" : "slow");
        if (attempt < 12) {
          await new Promise((r) => setTimeout(r, 5000));
          return tryHealth(attempt + 1);
        }
        done = true;
        setState(offline ? "offline" : "down");
      }
    };
    tryHealth(0);
    return () => {
      done = true;
      clearTimeout(slow);
    };
  }, []);

  // The landing page still wakes the server in the background, but shows no banner: it needs no server to read.
  if (pathname === "/") return null;
  if (state === "slow")
    return (
      <div role="status" className="bg-soon-soft px-4 py-2 text-center text-sm text-soon">
        {t("wakeSlow")}
      </div>
    );
  if (state === "offline" || state === "down")
    return (
      <div role="alert" className="bg-urgent-soft px-4 py-2 text-center text-sm text-urgent">
        {t(state === "offline" ? "offline" : "wakeDown")}
      </div>
    );
  return null;
}
