"use client";

// Line chart of the trust meter: coverage, the 90% target, and the share answered without an expert,
// against the number of field labels in calibration. Plain SVG: no chart library needed.
import { useState } from "react";
import type { CalibrationRun } from "@/lib/api";

const W = 420, H = 230, PAD = { l: 40, r: 12, t: 14, b: 38 };
const SERIES = [
  { key: "monitor_coverage", label: "Shortlist contains right disease", color: "#15803d" },
  { key: "monitor_answered", label: "Answered without expert", color: "#1d5fad" },
] as const;

export default function TrustChart({ runs }: { runs: CalibrationRun[] }) {
  const [hover, setHover] = useState<number | null>(null);
  if (runs.length === 0) return null;
  const xs = runs.map((_, i) => i);
  const x = (i: number) => PAD.l + (runs.length === 1 ? 0.5 : i / (xs.length - 1)) * (W - PAD.l - PAD.r);
  const y = (v: number) => PAD.t + (1 - v) * (H - PAD.t - PAD.b);
  const path = (k: (typeof SERIES)[number]["key"]) =>
    runs.map((r, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(r[k]).toFixed(1)}`).join(" ");
  const h = hover ?? runs.length - 1;

  return (
    <figure>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img"
        aria-label="Chart of shortlist coverage and answered-alone rate as expert labels are added"
        onMouseLeave={() => setHover(null)}>
        {[0, 0.25, 0.5, 0.75, 1].map((v) => (
          <g key={v}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} stroke="#e3e1d8" />
            <text x={PAD.l - 8} y={y(v) + 4} textAnchor="end" fontSize="12" fill="#7a837c">{v * 100}%</text>
          </g>
        ))}
        <line x1={PAD.l} x2={W - PAD.r} y1={y(0.9)} y2={y(0.9)} stroke="#7a837c" strokeDasharray="5 4" />
        <text x={W - PAD.r} y={y(0.9) - 5} textAnchor="end" fontSize="12" fill="#4b554e">90% promise</text>
        {SERIES.map((s) => (
          <path key={s.key} d={path(s.key)} fill="none" stroke={s.color} strokeWidth="2.5" strokeLinejoin="round" />
        ))}
        {runs.map((r, i) => (
          <g key={r.id}>
            {SERIES.map((s) => <circle key={s.key} cx={x(i)} cy={y(r[s.key])} r={i === h ? 5 : 3.5} fill={s.color} stroke="#fff" strokeWidth="2" />)}
            <rect x={x(i) - 14} y={PAD.t} width="28" height={H - PAD.t - PAD.b} fill="transparent" onMouseEnter={() => setHover(i)} />
            <text x={x(i)} y={H - PAD.b + 16} textAnchor="middle" fontSize="12" fill="#7a837c">{r.n_field_points}</text>
          </g>
        ))}
        <text x={(W + PAD.l) / 2} y={H - 4} textAnchor="middle" fontSize="12" fill="#4b554e">Field labels in calibration</text>
      </svg>
      <figcaption className="mt-2 flex flex-wrap items-center gap-x-5 gap-y-1 text-sm text-ink-2">
        {SERIES.map((s) => (
          <span key={s.key} className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: s.color }} />{s.label}
          </span>
        ))}
        <span className="ml-auto text-ink-3">
          {runs[h].note}: coverage {Math.round(runs[h].monitor_coverage * 100)}%, answered {Math.round(runs[h].monitor_answered * 100)}%
        </span>
      </figcaption>
    </figure>
  );
}
