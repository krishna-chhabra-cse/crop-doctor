"use client";

import { Moon, Sun } from "lucide-react";
import { useSyncExternalStore } from "react";

type Theme = "light" | "dark";

// The theme lives on <html data-theme>, set before paint by the inline script in layout.tsx.
const read = (): Theme => (document.documentElement.dataset.theme === "dark" ? "dark" : "light");
const listeners = new Set<() => void>();
const subscribe = (fn: () => void) => {
  listeners.add(fn);
  return () => listeners.delete(fn);
};

function setTheme(t: Theme) {
  document.documentElement.dataset.theme = t;
  document.querySelector('meta[name="theme-color"]')?.setAttribute("content", t === "dark" ? "#0e1311" : "#f6f7f4");
  try {
    localStorage.setItem("cd_theme", t);
  } catch {}
  listeners.forEach((fn) => fn());
}

export default function ThemeToggle() {
  const theme = useSyncExternalStore(subscribe, read, () => "light" as Theme);
  const dark = theme === "dark";
  const Icon = dark ? Sun : Moon;
  return (
    <button
      type="button"
      onClick={() => setTheme(dark ? "light" : "dark")}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      title={dark ? "Light mode" : "Dark mode"}
      className="flex h-12 w-12 items-center justify-center rounded-xl text-ink-2 hover:bg-surface-2 hover:text-ink"
    >
      <Icon className="h-6 w-6" aria-hidden="true" />
    </button>
  );
}
