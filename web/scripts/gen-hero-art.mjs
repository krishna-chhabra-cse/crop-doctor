// Crop Doctor hero art generator. Run: node scripts/gen-hero-art.mjs
//
// Built at build time, never in the browser, so the page without JavaScript still has its art.
// One whole potato plant is drawn twice, mirrored, its flower cluster reaching the centre:
//   pole A, FIELD (left):  the plant as the farmer knows it. Watercolour washes, wobbly ink, compound
//                          leaves with early-blight spots, white-lilac flowers, roots and tubers in a soil
//                          cross-section, sun and sky. Soft grammar, light key.
//   pole B, MODEL (right): the same plant as the model reads it. Leaves as pixel tiles with amber
//                          "attention" on the spots, the stem as a routed trace, flowers as concentric
//                          nodes, roots as circuit traces ending in vias, tubers as chips. Hard grammar,
//                          dark key.
// Output: components/immersive/heroArt.generated.ts

import { writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const W = 1600, H = 900, CX = 800, SOIL = 760;
const here = dirname(fileURLToPath(import.meta.url));
const OUT = join(here, "..", "components", "immersive", "heroArt.generated.ts");

const PALETTE = {
  paper: "#efe6d4",
  a: {
    ink: "#2b2418",
    sage: ["#3f5f2a", "#6f8f45", "#a9bd78"],
    ochre: ["#a8742c", "#cf9f52", "#ecd29c"],
    blight: ["#4e2c12", "#8a5426", "#c39150"],
    soil: ["#6b4a2c", "#9a7148", "#c9a77a"],
    petal: ["#f6f0f6", "#c9b6d9", "#8f72ad"],
    sky: ["#c9d8d4", "#e3d3b0"],
  },
  b: {
    ground: ["#101a2e", "#18274a", "#25406c"],
    tile: ["#2b6a87", "#4c98b3", "#8fd0dd", "#c4ecf0"],
    amber: ["#c9822a", "#f0b44a", "#ffd88a"],
    line: "#9fc4dd",
  },
};

// ═══ seeded randomness ═══
function mulberry32(a) {
  return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
let rnd = mulberry32(20261114);
const r = (a, b) => a + (b - a) * rnd();
const f = (n) => Math.round(n * 10) / 10;
const pick = (arr) => arr[Math.floor(rnd() * arr.length)];
const mx = (x) => 2 * CX - x;

// ═══ the plant, in pole-A coordinates (pole B mirrors x around CX) ═══
const quad = (p0, c, p1) => ({
  at: (t) => { const u = 1 - t; return [u * u * p0[0] + 2 * u * t * c[0] + t * t * p1[0], u * u * p0[1] + 2 * u * t * c[1] + t * t * p1[1]]; },
  ang: (t) => Math.atan2(2 * (1 - t) * (c[1] - p0[1]) + 2 * t * (p1[1] - c[1]), 2 * (1 - t) * (c[0] - p0[0]) + 2 * t * (p1[0] - c[0])),
  p0, c, p1,
});
const STEM = quad([300, SOIL + 10], [380, 470], [700, 470]);
const STEMS = [STEM];
const LEAFLETS = [];
// A compound leaf: a petiole with paired leaflets growing larger toward one big terminal leaflet.
function compoundLeaf(base, ang, len, s, spots) {
  const end = [base[0] + Math.cos(ang) * len, base[1] + Math.sin(ang) * len];
  const bend = [base[0] + Math.cos(ang + 0.25) * len * 0.55, base[1] + Math.sin(ang + 0.25) * len * 0.55];
  const pet = quad(base, bend, end);
  STEMS.push(pet);
  [[0.35, 0.55], [0.6, 0.75], [0.82, 0.9]].forEach(([t, k], i) => {
    const [x, y] = pet.at(t), a = pet.ang(t);
    for (const side of [-1, 1]) {
      const la = a + side * 1.0, rx = 34 * s * k, ry = 17 * s * k;
      LEAFLETS.push({ cx: x + Math.cos(la) * rx, cy: y + Math.sin(la) * rx, rx, ry, rot: la, spot: 0 });
    }
  });
  const a = pet.ang(1), rx = 50 * s, ry = 27 * s;
  LEAFLETS.push({ cx: end[0] + Math.cos(a) * rx * 0.85, cy: end[1] + Math.sin(a) * rx * 0.85, rx, ry, rot: a, spot: 0 });
  // blight on some leaflets of this leaf
  const mine = LEAFLETS.slice(-7);
  for (let k = 0; k < spots; k++) mine[Math.floor(rnd() * 7)].spot++;
}
//            t     angle  len  scale spots
[[0.18, -2.5, 150, 1.0, 0], [0.3, -0.7, 170, 1.15, 1], [0.45, -2.2, 160, 1.1, 1], [0.6, -0.35, 150, 1.25, 2], [0.72, -1.7, 150, 1.1, 1], [0.85, 0.55, 120, 1.0, 2], [0.5, 0.4, 120, 0.9, 0]].forEach(([t, a, l, s, sp]) => compoundLeaf(STEM.at(t), a, l, s, sp));
const inLeaflet = (x, y, L) => {
  const dx = x - L.cx, dy = y - L.cy, c = Math.cos(-L.rot), s = Math.sin(-L.rot);
  const u = dx * c - dy * s, v = dx * s + dy * c;
  const taper = 1 - 0.35 * Math.pow(Math.abs(u / L.rx), 3);
  return (u * u) / (L.rx * L.rx) + (v * v) / (L.ry * L.ry * taper * taper) <= 1;
};
const SPOTS = [];
LEAFLETS.forEach((L) => {
  for (let k = 0; k < L.spot; k++) {
    const u = r(-0.4, 0.4) * L.rx, v = r(-0.3, 0.3) * L.ry, c = Math.cos(L.rot), s = Math.sin(L.rot);
    SPOTS.push({ x: L.cx + u * c - v * s, y: L.cy + u * s + v * c, r: r(5, 10) * (L.rx / 45) });
  }
});
// Flower cluster at the stem's tip, reaching the centre.
const FLOWERS = [[728, 452, 22], [752, 494, 18], [706, 418, 16], [758, 438, 15], [724, 506, 13]].map(([x, y, s]) => ({ x, y, s }));
const FLOWER_STALKS = FLOWERS.map((F) => quad([700, 470], [(700 + F.x) / 2, Math.min(470, F.y) - 12], [F.x, F.y]));
// Underground: roots and tubers on stolons.
const TUBERS = [[220, 830, 46, 30, -0.2], [395, 850, 54, 34, 0.15], [520, 812, 36, 24, 0.4], [300, 878, 30, 20, 0]].map(([x, y, rx, ry, rot]) => ({ x, y, rx, ry, rot }));
const ROOTS = [];
for (let i = 0; i < 14; i++) { const a = r(0.6, 2.5), l = r(50, 130); ROOTS.push([[300, SOIL + 10], [300 + Math.cos(a) * l * 0.5 + r(-20, 20), SOIL + 10 + Math.sin(a) * l * 0.5], [300 + Math.cos(a) * l, SOIL + 10 + Math.sin(a) * l]]); }
const STOLONS = TUBERS.map((T) => [[300, SOIL + 14], [(300 + T.x) / 2, Math.max(SOIL + 20, T.y - 30)], [T.x, T.y - T.ry * 0.6]]);

// ═══ drawing helpers ═══
function smoothPath(pts) {
  const n = pts.length, mid = (a, b) => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
  let d = `M${f(mid(pts[n - 1], pts[0])[0])} ${f(mid(pts[n - 1], pts[0])[1])}`;
  for (let i = 0; i < n; i++) { const m = mid(pts[i], pts[(i + 1) % n]); d += `Q${f(pts[i][0])} ${f(pts[i][1])} ${f(m[0])} ${f(m[1])}`; }
  return d + "Z";
}
function leafPath(L, jitter, n = 24) {
  const pts = [], c = Math.cos(L.rot), s = Math.sin(L.rot);
  for (let i = 0; i < n; i++) {
    const th = (i / n) * Math.PI * 2, rr = 1 + r(-jitter, jitter);
    const u = Math.cos(th) * L.rx * rr, v = Math.sin(th) * L.ry * rr * (1 - 0.4 * Math.pow(Math.abs(Math.cos(th)), 3));
    pts.push([L.cx + u * c - v * s, L.cy + u * s + v * c]);
  }
  return smoothPath(pts);
}
function blob(cx, cy, rx, ry, jitter = 0.25, n = 16, rot = 0) {
  const pts = [], c = Math.cos(rot), s = Math.sin(rot);
  for (let i = 0; i < n; i++) { const th = (i / n) * Math.PI * 2, rr = 1 + r(-jitter, jitter), u = Math.cos(th) * rx * rr, v = Math.sin(th) * ry * rr; pts.push([cx + u * c - v * s, cy + u * s + v * c]); }
  return smoothPath(pts);
}
// A hand-inked line: two or three overlapping strokes with jittered width.
function ink(q, wMin, wMax, color, op = 0.85, passes = 2) {
  let s = "";
  for (let k = 0; k < passes; k++) {
    const j = () => r(-1.8, 1.8);
    s += `<path d="M${f(q.p0[0] + j())} ${f(q.p0[1] + j())}Q${f(q.c[0] + j())} ${f(q.c[1] + j())} ${f(q.p1[0] + j())} ${f(q.p1[1] + j())}" stroke="${color}" stroke-width="${f(r(wMin, wMax))}" opacity="${f(op * r(0.6, 1))}"/>`;
  }
  return s;
}
const qd = (q) => `M${f(q.p0[0])} ${f(q.p0[1])}Q${f(q.c[0])} ${f(q.c[1])} ${f(q.p1[0])} ${f(q.p1[1])}`;

// ═══ pole A: field ═══
function poleA() {
  const P = PALETTE.a;
  let sky = "", soil = "", leaf = "", detail = "", flowers = "", under = "";
  // sky: high-key washes, denser toward the centre
  for (let i = 0; i < 8; i++) sky += `<path d="${blob(r(60, 560), r(60, 380), r(120, 220), r(60, 130))}" fill="${pick([P.ochre[2], P.sky[1], P.sky[0]])}" opacity="${f(r(0.25, 0.5))}"/>`;
  for (let i = 0; i < 4; i++) sky += `<path d="${blob(r(80, 300), r(60, 200), r(60, 120), r(50, 100))}" fill="${P.ochre[1]}" opacity="${f(r(0.15, 0.3))}"/>`;
  // soil cross-section: a wobbly band with layered earth
  soil += `<path d="M-20 ${SOIL}${Array.from({ length: 18 }, (_, i) => `L${f(i * 50)} ${f(SOIL + r(-6, 6))}`).join("")}L830 ${SOIL + 6}L830 920L-20 920Z" fill="${P.soil[2]}" opacity=".55"/>`;
  for (let i = 0; i < 12; i++) soil += `<path d="${blob(r(0, 780), r(790, 900), r(90, 220), r(16, 40))}" fill="${pick(P.soil)}" opacity="${f(r(0.15, 0.4))}"/>`;
  // grass along the soil line
  for (let i = 0; i < 110; i++) { const x = r(-10, 800), h = r(14, 46); detail += `<path d="M${f(x)} ${f(SOIL + r(-2, 4))}q${f(r(-6, 6))} ${f(-h / 2)} ${f(r(-12, 12))} ${f(-h)}" stroke="${pick(P.sage)}" stroke-width="${f(r(0.6, 1.6))}" opacity="${f(r(0.4, 0.85))}"/>`; }
  // soil specks and pebbles
  for (let i = 0; i < 160; i++) detail += `<circle cx="${f(r(0, 800))}" cy="${f(r(SOIL + 8, 900))}" r="${f(r(0.6, 2.6))}" fill="${pick(P.soil)}" opacity="${f(r(0.3, 0.75))}"/>`;
  // roots, stolons, tubers
  ROOTS.forEach(([a, b, c]) => { detail += ink({ p0: a, c: b, p1: c }, 0.4, 1.0, P.soil[0], 0.7); under += `<path d="${qd({ p0: a, c: b, p1: c })}"/>`; });
  STOLONS.forEach(([a, b, c]) => { detail += ink({ p0: a, c: b, p1: c }, 1.2, 2.2, P.soil[0], 0.8); });
  TUBERS.forEach((T) => {
    for (let k = 0; k < 3; k++) soil += `<path d="${blob(T.x, T.y, T.rx, T.ry, 0.08, 18, T.rot)}" fill="${[P.ochre[1], P.soil[1], P.ochre[2]][k]}" opacity="${f(r(0.45, 0.7))}"/>`;
    detail += `<path d="${blob(T.x, T.y, T.rx, T.ry, 0.06, 18, T.rot)}" fill="none" stroke="${P.soil[0]}" stroke-width="${f(r(0.6, 1.2))}" opacity=".7"/>`;
    for (let k = 0; k < 4; k++) detail += `<path d="M${f(T.x + r(-0.6, 0.6) * T.rx)} ${f(T.y + r(-0.5, 0.5) * T.ry)}q2 -2 4 0" stroke="${P.soil[0]}" stroke-width=".8" fill="none" opacity=".7"/>`;
    under += `<ellipse cx="${T.x}" cy="${T.y}" rx="${T.rx}" ry="${T.ry}" transform="rotate(${f((T.rot * 180) / Math.PI)} ${T.x} ${T.y})"/>`;
  });
  // stems
  STEMS.forEach((q, i) => { detail += ink(q, i ? 1.0 : 2.4, i ? 2.0 : 4.2, P.sage[0], 0.9, i ? 2 : 3); under += `<path d="${qd(q)}"/>`; });
  // leaflets: three washes, then midrib and veins
  LEAFLETS.forEach((L) => {
    for (let k = 0; k < 3; k++) leaf += `<path d="${leafPath(L, 0.07)}" fill="${P.sage[(k + Math.floor(rnd() * 2)) % 3]}" opacity="${f(r(0.32, 0.55))}"/>`;
    under += `<path d="${leafPath(L, 0.02)}"/>`;
    const c = Math.cos(L.rot), s = Math.sin(L.rot);
    const a = [L.cx - c * L.rx * 0.95, L.cy - s * L.rx * 0.95], b = [L.cx + c * L.rx * 0.9, L.cy + s * L.rx * 0.9];
    detail += ink({ p0: a, c: [L.cx - s * 2, L.cy + c * 2], p1: b }, 0.4, 1.1, P.ink, 0.55);
    for (let k = -3; k <= 3; k++) {
      if (!k) continue;
      const t = (k + 4) / 8, bx = a[0] + (b[0] - a[0]) * t, by = a[1] + (b[1] - a[1]) * t, side = k % 2 ? 1 : -1;
      const ex = bx + (c * 0.45 - s * side) * L.ry * 0.85, ey = by + (s * 0.45 + c * side) * L.ry * 0.85;
      detail += `<path d="M${f(bx)} ${f(by)}L${f(ex)} ${f(ey)}" stroke="${P.ink}" stroke-width="${f(r(0.3, 0.7))}" opacity=".35"/>`;
    }
  });
  // early blight: yellow halo, brown lesion, concentric rings
  SPOTS.forEach((S) => {
    leaf += `<path d="${blob(S.x, S.y, S.r * 1.9, S.r * 1.7, 0.2)}" fill="${P.ochre[2]}" opacity=".6"/>`;
    leaf += `<path d="${blob(S.x, S.y, S.r, S.r * 0.92, 0.18)}" fill="${P.blight[1]}" opacity=".8"/>`;
    for (let k = 1; k <= 3; k++) detail += `<path d="${blob(S.x, S.y, S.r * k * 0.32, S.r * k * 0.3, 0.12, 10)}" fill="none" stroke="${P.blight[0]}" stroke-width="${f(r(0.4, 0.9))}" opacity=".8"/>`;
    under += `<circle cx="${f(S.x)}" cy="${f(S.y)}" r="${f(S.r)}"/>`;
  });
  // flowers: five petals, a yellow cone
  FLOWER_STALKS.forEach((q) => { detail += ink(q, 0.6, 1.2, P.sage[0], 0.8); under += `<path d="${qd(q)}"/>`; });
  FLOWERS.forEach((F) => {
    const rot = r(0, 1.2);
    for (let k = 0; k < 5; k++) {
      const a = rot + (k / 5) * Math.PI * 2, px = F.x + Math.cos(a) * F.s * 0.55, py = F.y + Math.sin(a) * F.s * 0.55;
      flowers += `<path d="${blob(px, py, F.s * 0.55, F.s * 0.38, 0.1, 12, a)}" fill="${pick([P.petal[0], P.petal[0], P.petal[1]])}" opacity=".92"/>`;
      flowers += `<path d="M${f(F.x)} ${f(F.y)}L${f(F.x + Math.cos(a) * F.s * 0.9)} ${f(F.y + Math.sin(a) * F.s * 0.9)}" stroke="${P.petal[2]}" stroke-width=".5" opacity=".6"/>`;
    }
    flowers += `<path d="${blob(F.x, F.y, F.s * 0.2, F.s * 0.2, 0.1, 8)}" fill="#e9b52f"/>`;
    under += `<circle cx="${F.x}" cy="${F.y}" r="${F.s}"/>`;
  });
  // sun rays, upper left
  for (let i = 0; i < 16; i++) { const a = r(0.08, 1.3), l = r(260, 560); detail += `<path d="M30 40L${f(30 + Math.cos(a) * l)} ${f(40 + Math.sin(a) * l)}" stroke="${P.ochre[0]}" stroke-width="${f(r(0.3, 0.9))}" opacity="${f(r(0.15, 0.35))}"/>`; }
  // drifting pollen near the flowers
  for (let i = 0; i < 40; i++) detail += `<circle cx="${f(r(560, 800))}" cy="${f(r(330, 560))}" r="${f(r(0.8, 2))}" fill="${pick([P.ochre[1], P.petal[1]])}" opacity="${f(r(0.4, 0.8))}"/>`;
  const art =
    `<g filter="url(#cd-gran)" style="mix-blend-mode:multiply">${sky}${soil}</g>` +
    `<g filter="url(#cd-wobble)" style="mix-blend-mode:multiply">${leaf}</g>` +
    `<g fill="none" stroke-linecap="round">${detail}</g>` +
    `<g filter="url(#cd-wobble)">${flowers}</g>`;
  return { art, under: `<g fill="none" stroke="currentColor" stroke-width=".6">${under}</g>` };
}

// ═══ pole B: model ═══
function poleB() {
  rnd = mulberry32(911);
  const P = PALETTE.b, T = 16;
  let ground = `<rect x="${CX - 90}" y="0" width="${W - CX + 90}" height="${H}" fill="url(#cd-bground)"/>`;
  for (let i = 0; i < 6; i++) ground += `<rect x="${f(r(900, 1500))}" y="${f(r(0, 700))}" width="${f(r(80, 260))}" height="${f(r(40, 160))}" fill="${P.ground[2]}" opacity="${f(r(0.12, 0.3))}"/>`;
  let grid = "", tiles = "", marks = "", under = "";
  for (let x = CX + 28; x <= W; x += 56) grid += `<path d="M${x} 0V${H}"/>`;
  for (let y = 4; y <= H; y += 56) grid += `<path d="M${CX} ${y}H${W}"/>`;
  under += grid;
  // the soil line as a hard rule, the underground as a darker band
  marks += `<rect x="${CX}" y="${SOIL + 10}" width="${W - CX}" height="${H - SOIL}" fill="${P.ground[0]}" opacity=".55"/>`;
  marks += `<path d="M${CX} ${SOIL + 10}H${W}" stroke="${P.tile[1]}" stroke-width="1" stroke-dasharray="6 4" opacity=".7"/>`;
  // leaves sampled on a T-unit grid; tiles near a lesion glow amber
  const spotsB = SPOTS.map((S) => ({ x: mx(S.x), y: S.y, r: S.r }));
  for (let x = CX + 4; x < W; x += T) {
    for (let y = 0; y < SOIL; y += T) {
      const px = x + T / 2, py = y + T / 2;
      if (!LEAFLETS.some((L) => inLeaflet(mx(px), py, L))) continue;
      let heat = 0;
      spotsB.forEach((S) => { heat = Math.max(heat, 1 - Math.hypot(px - S.x, py - S.y) / (S.r * 2.8)); });
      const fill = heat > 0.55 ? P.amber[2] : heat > 0.25 ? P.amber[1] : heat > 0 ? P.amber[0] : P.tile[Math.floor(r(0, 3))];
      tiles += `<rect x="${x + 1}" y="${y + 1}" width="${T - 2}" height="${T - 2}" fill="${fill}" opacity="${f(heat > 0 ? 0.95 : r(0.5, 0.95))}"/>`;
    }
  }
  // stems as routed traces
  const route = (q) => { const pts = []; for (let t = 0; t <= 1.0001; t += 0.08) { const [x, y] = q.at(t); pts.push([mx(x), y]); } return `M${f(pts[0][0])} ${f(pts[0][1])}` + pts.slice(1).map(([x, y]) => `H${f(x)}V${f(y)}`).join(""); };
  STEMS.forEach((q, i) => { const d = route(q); marks += `<path d="${d}" stroke="${P.tile[i ? 1 : 2]}" stroke-width="${i ? 1.2 : 2.4}" fill="none"/>`; under += `<path d="${d}"/>`; });
  FLOWER_STALKS.forEach((q) => { marks += `<path d="${route(q)}" stroke="${P.tile[1]}" stroke-width="1" fill="none"/>`; });
  // flowers as concentric nodes
  FLOWERS.forEach((F) => {
    const x = mx(F.x);
    marks += `<circle cx="${x}" cy="${F.y}" r="${F.s}" fill="${P.ground[1]}" stroke="${P.tile[2]}" stroke-width="1"/>`;
    marks += `<circle cx="${x}" cy="${F.y}" r="${f(F.s * 0.62)}" fill="none" stroke="${P.tile[3]}" stroke-width=".8" stroke-dasharray="2 2"/>`;
    marks += `<circle cx="${x}" cy="${F.y}" r="${f(F.s * 0.25)}" fill="${P.amber[1]}"/>`;
    for (let k = 0; k < 5; k++) { const a = (k / 5) * Math.PI * 2; marks += `<rect x="${f(x + Math.cos(a) * F.s - 1.5)}" y="${f(F.y + Math.sin(a) * F.s - 1.5)}" width="3" height="3" fill="${P.tile[3]}"/>`; }
    under += `<circle cx="${x}" cy="${F.y}" r="${F.s}"/>`;
  });
  // roots as circuit traces ending in vias; tubers as chips with pins
  ROOTS.forEach(([a, , c]) => {
    const x0 = mx(a[0]), x1 = mx(c[0]), ym = (a[1] + c[1]) / 2;
    const d = `M${f(x0)} ${f(a[1])}V${f(ym)}H${f(x1)}V${f(c[1])}`;
    marks += `<path d="${d}" stroke="${P.tile[1]}" stroke-width=".9" fill="none" opacity=".8"/><circle cx="${f(x1)}" cy="${f(c[1])}" r="2.4" fill="none" stroke="${P.tile[2]}"/>`;
    under += `<path d="${d}"/>`;
  });
  TUBERS.forEach((T2) => {
    const x = mx(T2.x), w = T2.rx * 1.6, h = T2.ry * 1.5;
    marks += `<rect x="${f(x - w / 2)}" y="${f(T2.y - h / 2)}" width="${f(w)}" height="${f(h)}" rx="4" fill="${P.ground[2]}" stroke="${P.tile[2]}" stroke-width="1"/>`;
    for (let k = 1; k < 5; k++) {
      const px = x - w / 2 + (w * k) / 5;
      marks += `<path d="M${f(px)} ${f(T2.y - h / 2)}v-5M${f(px)} ${f(T2.y + h / 2)}v5" stroke="${P.tile[2]}" stroke-width="1"/>`;
    }
    marks += `<rect x="${f(x - 4)}" y="${f(T2.y - 4)}" width="8" height="8" fill="${P.amber[1]}" opacity=".85"/>`;
    under += `<rect x="${f(x - w / 2)}" y="${f(T2.y - h / 2)}" width="${f(w)}" height="${f(h)}"/>`;
  });
  STOLONS.forEach(([a, , c]) => { marks += `<path d="M${f(mx(a[0]))} ${f(a[1])}V${f(c[1] - 10)}H${f(mx(c[0]))}V${f(c[1])}" stroke="${P.tile[0]}" stroke-width="1.6" fill="none"/>`; });
  // detection boxes on the lesions, registration ticks
  spotsB.forEach((S) => {
    const b = S.r * 2.6, x = S.x - b / 2, y = S.y - b / 2, t = Math.min(6, b / 3);
    marks += `<path d="M${f(x)} ${f(y + t)}V${f(y)}H${f(x + t)}M${f(x + b - t)} ${f(y)}H${f(x + b)}V${f(y + t)}M${f(x + b)} ${f(y + b - t)}V${f(y + b)}H${f(x + b - t)}M${f(x + t)} ${f(y + b)}H${f(x)}V${f(y + b - t)}" stroke="${P.amber[1]}" stroke-width="1.2" fill="none"/>`;
    under += `<rect x="${f(x)}" y="${f(y)}" width="${f(b)}" height="${f(b)}"/>`;
  });
  // the shortlist: three ranked bars, upper right
  [[0.86, P.amber[1]], [0.34, P.tile[1]], [0.12, P.tile[0]]].forEach(([v, c], i) => {
    marks += `<rect x="1230" y="${110 + i * 20}" width="${f(v * 280)}" height="8" fill="${c}"/>`;
    marks += `<path d="M1230 ${122 + i * 20}H1510" stroke="${P.line}" stroke-width=".5" opacity=".35"/>`;
  });
  // a constellation of nodes and links, the model's other features, denser toward the centre
  const nodes = Array.from({ length: 34 }, () => [CX + 60 + Math.pow(rnd(), 1.4) * 720, r(40, 420)]);
  nodes.forEach(([x, y], i) => {
    const [x2, y2] = nodes[(i * 7 + 3) % nodes.length];
    if (Math.hypot(x2 - x, y2 - y) < 220) marks += `<path d="M${f(x)} ${f(y)}L${f(x2)} ${f(y2)}" stroke="${P.line}" stroke-width=".5" opacity=".35"/>`;
    marks += `<circle cx="${f(x)}" cy="${f(y)}" r="${f(r(1.4, 3))}" fill="${pick(P.tile)}" opacity="${f(r(0.5, 0.95))}"/>`;
  });
  for (let i = 0; i < 150; i++) {
    const x = CX + 40 + Math.pow(rnd(), 1.5) * 760, y = r(0, H), s = pick([2, 2, 3]);
    marks += `<rect x="${f(x)}" y="${f(y)}" width="${s}" height="${s}" fill="${pick(P.tile)}" opacity="${f(r(0.2, 0.6))}"/>`;
  }
  // scan line across the plant
  marks += `<path d="M${CX + 40} 300H${W - 40}" stroke="${P.amber[1]}" stroke-width=".8" opacity=".5"/>`;
  const art = ground + `<g stroke="${P.line}" stroke-width=".6" opacity=".2">${grid}</g>` + tiles + marks;
  return { art, under: `<g fill="none" stroke="currentColor" stroke-width=".6">${under}</g>` };
}

const A = poleA();
const B = poleB();
const defs =
  `<filter id="cd-gran" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="1" numOctaves="2" seed="7"/><feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 -1.4 1.25"/><feComposite in="SourceGraphic" operator="in"/></filter>` +
  `<filter id="cd-wobble"><feTurbulence type="fractalNoise" baseFrequency=".035" numOctaves="2" seed="3"/><feDisplacementMap in="SourceGraphic" scale="3"/></filter>` +
  `<linearGradient id="cd-bground" x1="0" x2="1"><stop offset="0" stop-color="${PALETTE.b.ground[0]}" stop-opacity="0"/><stop offset=".11" stop-color="${PALETTE.b.ground[0]}" stop-opacity=".92"/><stop offset=".5" stop-color="${PALETTE.b.ground[1]}"/><stop offset="1" stop-color="${PALETTE.b.ground[0]}"/></linearGradient>`;

const GEOMETRY = { w: W, h: H, meet: [CX, 470], logo: [CX, 300], focalA: [560, 520], focalB: [1040, 520] };
const ts = `// GENERATED by scripts/gen-hero-art.mjs. Do not edit by hand.
export const GEOMETRY = ${JSON.stringify(GEOMETRY)} as const;
export const PARTICLE_COLORS = ${JSON.stringify({ a: [...PALETTE.a.sage, PALETTE.a.ochre[1], PALETTE.a.petal[1], PALETTE.a.blight[1]], b: [...PALETTE.b.tile, PALETTE.b.amber[1]] })};
export const PAPER = ${JSON.stringify(PALETTE.paper)};
export const DEFS = ${JSON.stringify(defs)};
export const POLE_A = ${JSON.stringify(A.art)};
export const POLE_B = ${JSON.stringify(B.art)};
export const UNDER_A = ${JSON.stringify(A.under)};
export const UNDER_B = ${JSON.stringify(B.under)};
`;
writeFileSync(OUT, ts);
console.log(`wrote ${OUT} (${(ts.length / 1024).toFixed(1)} KB)`);
