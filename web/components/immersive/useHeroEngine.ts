"use client";

/* Crop Doctor hero engine.
 *
 *   scroll ─► targetP ─► smoothing (rAF) ─► p ─► derive() ─► masks, camera, logo, CSS vars
 *   p: −1 (FIELD survives) ··· 0 (both leaves meet) ··· +1 (MODEL survives)
 *
 * The hero is a tall section with a sticky stage. When you start scrolling, the side your pointer is on
 * stays and the other leaf dissolves: the field's watercolour lifts off in round blots, the model's pixels
 * drop out tile by tile. Then the page settles into a split: the surviving leaf holds its half and the
 * content column opens where the other one was. Everything is a pure function of p and `read`, so every
 * state can be reached backwards and reproduced.
 *
 * Without JavaScript, or with reduced motion, none of this runs: .im never gets im-motion and the page is
 * the plain composed hero followed by the document.
 *
 * Review switches: ?lean=a|b  ?progress=-1…1  ?read=0…1  ?motion=off  ?debug=1
 */
import { useEffect, type RefObject } from "react";
import { GEOMETRY, PARTICLE_COLORS } from "./heroArt.generated";

// ═══ CONFIG ═══
const DEFAULT_PATH = -1; // farmers first: with no pointer, the field stays
const CELL = 25; // art units; 32 cells across each half
const RATE_SCROLL = 9;
const RATE_LEAN = 4;
const MAX_PARTICLES = 400;
const SVGNS = "http://www.w3.org/2000/svg";

// ═══ UTILITIES ═══
const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const ease = (x: number) => x * x * (3 - 2 * x);
function mulberry32(a: number) {
  return () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
const smoothNoise = (x: number, y: number) => 0.5 + 0.25 * Math.sin(x * 0.011 + 1.3) * Math.cos(y * 0.013 - 0.4) + 0.25 * Math.sin((x + y) * 0.027 + 2.1);

type Cell = { x: number; y: number; t: number; el: SVGElement; on: boolean; r: number; side: -1 | 1 };
type Particle = { x: number; y: number; vx: number; vy: number; life: number; max: number; c: string; s: number };

// ═══ DERIVE: every visual quantity from (p, read) ═══
export function derive(p: number, read: number, vw: number, vh: number) {
  const hp = Math.abs(p);
  const path = p < 0 ? -1 : 1;
  const dissolve = clamp((hp - 0.04) / 0.5);
  const s0 = Math.max(vw / GEOMETRY.w, vh / GEOMETRY.h);
  const ox = (vw - GEOMETRY.w * s0) / 2, oy = (vh - GEOMETRY.h * s0) / 2;
  // camera: the survivor's focal point lands 25% from its own edge (10% on narrow screens), scale ≤ 1.15
  const wide = vw >= 960;
  const k = wide ? 1.1 : 1;
  const [fxu, fyu] = path < 0 ? GEOMETRY.focalA : GEOMETRY.focalB;
  const fx = ox + fxu * s0, fy = oy + fyu * s0;
  const want = wide ? (path < 0 ? 0.25 * vw : 0.75 * vw) : path < 0 ? 0.1 * vw : 0.9 * vw;
  let tx = want - fx * k, ty = vh / 2 - fy * k;
  // the survivor fills its whole half: its clipped inner edge reaches the column
  const seam = (ox + (GEOMETRY.w / 2) * s0) * k;
  if (wide) tx = path < 0 ? Math.max(tx, vw / 2 - seam) : Math.min(tx, vw / 2 - seam);
  // never expose the art's edge
  const left = ox * k, right = (ox + GEOMETRY.w * s0) * k, top = oy * k, bottom = (oy + GEOMETRY.h * s0) * k;
  tx = Math.min(tx, -left);
  tx = Math.max(tx, vw - right);
  ty = Math.min(ty, -top);
  ty = Math.max(ty, vh - bottom);
  const e = ease(read);
  return {
    hp, path, dissolve, s0, ox, oy,
    cam: { k: 1 + (k - 1) * e, tx: tx * e, ty: ty * e },
    split: hp * 160 * s0,
    caps: 1 - clamp((hp - 0.12) / 0.35),
    a: path < 0 ? hp : 0,
    b: path > 0 ? hp : 0,
  };
}

export function useHeroEngine(rootRef: RefObject<HTMLElement | null>) {
  useEffect(() => {
    const root = rootRef.current;
    if (!root) return;
    const q = new URLSearchParams(location.search);
    const mq = matchMedia("(prefers-reduced-motion: reduce)");
    if (q.get("motion") === "off" || mq.matches) {
      const onChange = () => !mq.matches && location.reload();
      mq.addEventListener("change", onChange);
      return () => mq.removeEventListener("change", onChange);
    }

    // ═══ DOM ═══
    const hero = root.querySelector<HTMLElement>(".im-hero")!;
    const svg = root.querySelector<SVGSVGElement>(".im-art__main")!;
    const poleA = svg.querySelector<SVGGElement>("#cd-pole-a")!;
    const poleB = svg.querySelector<SVGGElement>("#cd-pole-b")!;
    const cellsA = svg.querySelector<SVGGElement>("#cd-cells-a")!;
    const cellsB = svg.querySelector<SVGGElement>("#cd-cells-b")!;
    const logo = root.querySelector<HTMLElement>(".im-logo")!;
    const canvas = root.querySelector<HTMLCanvasElement>(".im-particles")!;
    const ctx = canvas.getContext("2d")!;
    const pathA = root.querySelector<HTMLElement>(".im-path--a")!;
    const pathB = root.querySelector<HTMLElement>(".im-path--b")!;
    const debug = q.get("debug") === "1" ? document.createElement("pre") : null;
    if (debug) { Object.assign(debug.style, { position: "fixed", left: "8px", bottom: "8px", zIndex: "50", font: "12px monospace", background: "#fff", padding: "4px 6px" }); document.body.append(debug); }
    root.classList.add("im-motion");

    // ═══ CELLS: the dissolve masks ═══
    const rand = mulberry32(42);
    const cells: Cell[] = [];
    for (const side of [-1, 1] as const) {
      const group = side < 0 ? cellsA : cellsB;
      for (let gx = 0; gx < GEOMETRY.w / 2 / CELL; gx++) {
        for (let gy = 0; gy < GEOMETRY.h / CELL; gy++) {
          const x = side < 0 ? GEOMETRY.w / 2 - (gx + 0.5) * CELL : GEOMETRY.w / 2 + (gx + 0.5) * CELL;
          const y = (gy + 0.5) * CELL;
          const dist = gx / (GEOMETRY.w / 2 / CELL); // 0 at the centre: the side facing the centre goes first
          const noise = side < 0 ? smoothNoise(x, y) : rand();
          const t = clamp(0.68 * dist + 0.3 * noise);
          let el: SVGElement;
          if (side < 0) { // soft: blots, like water lifting pigment
            el = document.createElementNS(SVGNS, "circle");
            el.setAttribute("cx", String(x)); el.setAttribute("cy", String(y)); el.setAttribute("r", "0");
          } else { // hard: tiles lifting off a grid
            el = document.createElementNS(SVGNS, "rect");
            el.setAttribute("x", String(x - CELL / 2)); el.setAttribute("y", String(y - CELL / 2));
            el.setAttribute("width", String(CELL + 1)); el.setAttribute("height", String(CELL + 1));
            el.setAttribute("visibility", "hidden");
          }
          group.append(el);
          cells.push({ x, y, t, el, on: false, r: -1, side });
        }
      }
    }

    // ═══ STATE ═══
    let vw = innerWidth, vh = innerHeight, heroTop = 0, travel = 1;
    let p = 0, targetP = 0, lean = 0, targetLean = 0, path = DEFAULT_PATH;
    let pointerX: number | null = null, lastX = -1, lastY = -1;
    let raf = 0, last = performance.now();
    const particles: Particle[] = [];
    const cache = new Map<string, string>();
    const setVar = (el: HTMLElement | SVGElement, prop: string, v: string) => {
      const key = prop + (el === root ? "" : el.id || el.className);
      if (cache.get(key) === v) return;
      cache.set(key, v);
      if (prop.startsWith("--")) el.style.setProperty(prop, v);
      else el.setAttribute(prop, v);
    };
    const forcedPath = q.get("lean") === "a" ? -1 : q.get("lean") === "b" ? 1 : 0;
    const frozenP = q.has("progress") ? clamp(Number(q.get("progress")), -1, 1) : null;
    const frozenRead = q.has("read") ? clamp(Number(q.get("read"))) : null;

    // ═══ MEASURE (resize only) ═══
    const measure = () => {
      vw = innerWidth; vh = innerHeight;
      heroTop = hero.getBoundingClientRect().top + scrollY;
      travel = Math.max(1, hero.offsetHeight - vh);
      const dpr = Math.min(devicePixelRatio || 1, 2);
      canvas.width = vw * dpr; canvas.height = vh * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      cache.clear();
      onScroll();
    };

    // ═══ INPUT ═══
    function onScroll() {
      const hp = frozenP !== null ? Math.abs(frozenP) : frozenRead !== null ? 1 : clamp((scrollY - heroTop) / travel);
      if (hp < 0.08 && frozenP === null) {
        path = forcedPath || DEFAULT_PATH; // the dark model side always dissolves; the farmer's field stays
      }
      if (frozenP !== null) path = frozenP < 0 ? -1 : frozenP > 0 ? 1 : forcedPath || DEFAULT_PATH;
      targetP = path * hp;
      kick();
    }
    const onPointer = (e: PointerEvent) => {
      if (e.pointerType === "touch") return;
      if (e.clientX === lastX && e.clientY === lastY) return; // synthetic move after load or scroll
      if (e.clientX === 0 && e.clientY === 0) return;
      lastX = e.clientX; lastY = e.clientY; pointerX = e.clientX;
      targetLean = clamp((e.clientX / vw) * 2 - 1, -1, 1);
      onScroll();
    };

    // ═══ RENDER ═══
    const emit = (c: Cell, d: ReturnType<typeof derive>) => {
      if (particles.length >= MAX_PARTICLES) return;
      const px = (d.ox + c.x * d.s0) * d.cam.k + d.cam.tx, py = (d.oy + c.y * d.s0) * d.cam.k + d.cam.ty;
      const colors = c.side < 0 ? PARTICLE_COLORS.a : PARTICLE_COLORS.b;
      const n = 2 + Math.floor(Math.random() * 3);
      for (let i = 0; i < n; i++) {
        const max = 0.8 + Math.random() * 0.8;
        particles.push({ x: px, y: py, vx: c.side * (20 + Math.random() * 60), vy: -10 - Math.random() * 40, life: max, max, c: colors[Math.floor(Math.random() * colors.length)], s: c.side < 0 ? 2 + Math.random() * 3 : 2 + Math.floor(Math.random() * 3) });
      }
    };

    const render = (dt: number, forward: boolean) => {
      const read = frozenRead ?? clamp((Math.abs(p) - 0.7) / 0.3);
      const d = derive(p, read, vw, vh);
      const loser = d.hp < 0.005 ? 0 : d.path < 0 ? 1 : -1;

      // masks: only cells whose state changed
      for (const c of cells) {
        const dis = c.side === loser ? d.dissolve * 1.06 : 0;
        if (c.side < 0) {
          const r = Math.round(CELL * 0.95 * clamp((dis - c.t) / 0.09) * 10) / 10;
          if (r !== c.r) { c.el.setAttribute("r", String(r)); if (r > 0 && c.r <= 0 && forward) emit(c, d); c.r = r; }
        } else {
          const on = dis > c.t;
          if (on !== c.on) { c.el.setAttribute("visibility", on ? "visible" : "hidden"); if (on && forward) emit(c, d); c.on = on; }
        }
      }
      const clip = d.hp > 0.005;
      setVar(poleA, "clip-path", clip ? "url(#cd-clip-a)" : "none");
      setVar(poleB, "clip-path", clip ? "url(#cd-clip-b)" : "none");
      setVar(poleA, "visibility", loser === -1 && d.dissolve >= 1 ? "hidden" : "visible");
      setVar(poleB, "visibility", loser === 1 && d.dissolve >= 1 ? "hidden" : "visible");
      // the losing side also fades as a whole, so its ground (the dark one especially) is gone early
      const fade = (1 - clamp(d.dissolve / 0.6)).toFixed(3);
      setVar(poleA, "opacity", loser === -1 ? fade : "1");
      setVar(poleB, "opacity", loser === 1 ? fade : "1");
      // hover preview: the pole under the pointer leans toward the centre
      const l = d.hp < 0.02 ? lean : 0;
      setVar(poleA, "transform", `translate(${(Math.max(0, -l) * 14).toFixed(1)} 0)`);
      setVar(poleB, "transform", `translate(${(-Math.max(0, l) * 14).toFixed(1)} 0)`);

      svg.style.transform = `translate(${d.cam.tx.toFixed(1)}px, ${d.cam.ty.toFixed(1)}px) scale(${d.cam.k.toFixed(4)})`;
      setVar(logo, "--split", d.split.toFixed(1));
      setVar(root, "--progress", p.toFixed(3));
      setVar(root, "--a", d.a.toFixed(3));
      setVar(root, "--b", d.b.toFixed(3));
      setVar(root, "--lean", lean.toFixed(3));
      setVar(root, "--caps", d.caps.toFixed(3));
      setVar(root, "--read", read.toFixed(3));

      // path: the class, and §02 for the world you came in through
      const pa = path < 0;
      root.classList.toggle("im-path-a", pa);
      root.classList.toggle("im-path-b", !pa);

      // particles
      ctx.clearRect(0, 0, vw, vh);
      for (let i = particles.length - 1; i >= 0; i--) {
        const pt = particles[i];
        pt.life -= dt;
        if (pt.life <= 0) { particles.splice(i, 1); continue; }
        pt.x += pt.vx * dt; pt.y += pt.vy * dt; pt.vy -= 12 * dt;
        ctx.globalAlpha = clamp(pt.life / pt.max) * 0.85;
        ctx.fillStyle = pt.c;
        if (pt.s % 1) { ctx.beginPath(); ctx.arc(pt.x, pt.y, pt.s / 2, 0, 6.283); ctx.fill(); } else ctx.fillRect(pt.x, pt.y, pt.s, pt.s);
      }
      ctx.globalAlpha = 1;
      if (debug) debug.textContent = `p ${p.toFixed(3)} path ${path} read ${read.toFixed(2)} particles ${particles.length}`;
    };

    const frame = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const before = p;
      p += (targetP - p) * (1 - Math.exp(-RATE_SCROLL * dt));
      lean += (targetLean - lean) * (1 - Math.exp(-RATE_LEAN * dt));
      if (Math.abs(targetP - p) < 1e-4) p = targetP;
      render(dt, Math.abs(p) > Math.abs(before));
      raf = Math.abs(targetP - p) > 1e-4 || Math.abs(targetLean - lean) > 1e-3 || particles.length ? requestAnimationFrame(frame) : 0;
    };
    function kick() {
      if (!raf) { last = performance.now(); raf = requestAnimationFrame(frame); }
    }

    // ═══ BOOT ═══
    const ro = new ResizeObserver(measure);
    ro.observe(document.documentElement);
    addEventListener("scroll", onScroll, { passive: true });
    addEventListener("pointermove", onPointer, { passive: true });
    const onMotionPref = () => mq.matches && location.reload();
    mq.addEventListener("change", onMotionPref);
    measure();
    if (frozenP !== null) { p = targetP; render(0, false); }
    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      removeEventListener("scroll", onScroll);
      removeEventListener("pointermove", onPointer);
      mq.removeEventListener("change", onMotionPref);
      debug?.remove();
      root.classList.remove("im-motion", "im-path-a", "im-path-b");
      cellsA.replaceChildren(); cellsB.replaceChildren();
      pathA.hidden = pathB.hidden = false; pathA.inert = pathB.inert = false;
    };
  }, [rootRef]);
}
