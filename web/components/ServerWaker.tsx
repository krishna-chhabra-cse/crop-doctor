"use client";

// The backend runs on Render's free plan, which sleeps after 15 minutes without visitors and takes
// about a minute to wake up. We ping it as soon as anyone opens the site, and tell them if it's waking.
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function ServerWaker() {
  const [state, setState] = useState<"checking" | "slow" | "ok" | "down">("checking");

  useEffect(() => {
    let done = false;
    const slow = setTimeout(() => !done && setState("slow"), 2500);
    const tryHealth = async (attempt: number): Promise<void> => {
      try {
        await api.health();
        done = true;
        setState("ok");
      } catch {
        if (attempt < 12) {
          await new Promise((r) => setTimeout(r, 5000));
          return tryHealth(attempt + 1);
        }
        done = true;
        setState("down");
      }
    };
    tryHealth(0);
    return () => clearTimeout(slow);
  }, []);

  if (state === "slow")
    return (
      <div role="status" className="bg-amber-soft px-4 py-2 text-center text-sm text-amber">
        Waking up the server… free hosting sleeps when nobody uses it. This takes about a minute the first time.
      </div>
    );
  if (state === "down")
    return (
      <div role="alert" className="bg-red-soft px-4 py-2 text-center text-sm text-red">
        The server isn&apos;t responding right now. Please try again in a few minutes.
      </div>
    );
  return null;
}
