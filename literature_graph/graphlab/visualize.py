"""Write an interactive, single-file HTML explorer for the graph."""
from __future__ import annotations

import html
import json
from pathlib import Path

import networkx as nx

COLORS = {
    "paper": "#2563eb",
    "concept": "#16a34a",
    "dataset": "#d97706",
    "author": "#9ca3af",
    "domain": "#9333ea",
    "category": "#64748b",
}
SHAPES = {"paper": "dot", "domain": "diamond", "dataset": "square", "category": "triangle"}

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Research Graph</title>
<script src="https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"></script>
<style>
  :root { --bg:#fff; --fg:#111827; --muted:#6b7280; --panel:#f9fafb; --line:#e5e7eb; }
  @media (prefers-color-scheme: dark) { :root { --bg:#0b0f17; --fg:#e5e7eb; --muted:#9ca3af; --panel:#111827; --line:#1f2937; } }
  * { box-sizing: border-box; }
  body { margin:0; font:14px/1.45 system-ui, sans-serif; background:var(--bg); color:var(--fg); display:flex; height:100vh; }
  #net { flex:1; min-width:0; }
  aside { width:340px; border-left:1px solid var(--line); background:var(--panel); padding:16px; overflow:auto; }
  h1 { font-size:16px; margin:0 0 4px; } .muted { color:var(--muted); }
  .legend span { display:inline-flex; align-items:center; gap:6px; margin:0 10px 6px 0; }
  .legend i { width:10px; height:10px; border-radius:50%; display:inline-block; }
  label { display:block; margin:4px 0; } input[type=search] { width:100%; padding:6px 8px; margin:10px 0; border:1px solid var(--line); border-radius:6px; background:var(--bg); color:var(--fg); }
  #detail { margin-top:14px; border-top:1px solid var(--line); padding-top:12px; } a { color:#3b82f6; }
  @media (max-width: 720px) { body { flex-direction:column; } aside { width:auto; height:45vh; border-left:0; border-top:1px solid var(--line); } }
</style></head>
<body>
<div id="net"></div>
<aside>
  <h1>Research Graph</h1>
  <div class="muted">__STATS__</div>
  <input id="q" type="search" placeholder="Find a paper, concept, author…">
  <div class="legend" id="legend"></div>
  <div id="toggles"></div>
  <div id="detail" class="muted">Click a node to see its details and neighbors.</div>
</aside>
<script>
const DATA = __DATA__, COLORS = __COLORS__;
const nodes = new vis.DataSet(DATA.nodes), edges = new vis.DataSet(DATA.edges);
const hidden = new Set(["author", "category"]);
const net = new vis.Network(document.getElementById("net"), {
  nodes: new vis.DataView(nodes, { filter: n => !hidden.has(n.kind) }), edges
}, {
  physics: { solver: "forceAtlas2Based", stabilization: { iterations: 300 } },
  nodes: { font: { size: 12, color: getComputedStyle(document.body).color } },
  edges: { color: { opacity: 0.35 }, smooth: false }, interaction: { hover: true }
});
const legend = document.getElementById("legend"), toggles = document.getElementById("toggles");
for (const [kind, color] of Object.entries(COLORS)) {
  const n = DATA.nodes.filter(x => x.kind === kind).length;
  legend.insertAdjacentHTML("beforeend", `<span><i style="background:${color}"></i>${kind} (${n})</span>`);
  const box = document.createElement("label");
  box.innerHTML = `<input type="checkbox" ${hidden.has(kind) ? "" : "checked"}> show ${kind === "category" ? "categories" : kind + "s"}`;
  box.querySelector("input").onchange = e => { e.target.checked ? hidden.delete(kind) : hidden.add(kind); net.setData({ nodes: new vis.DataView(nodes, { filter: n => !hidden.has(n.kind) }), edges }); };
  toggles.appendChild(box);
}
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;" }[c]));
function show(id) {
  const n = nodes.get(id); if (!n) return;
  const nb = net.getConnectedNodes(id).map(x => nodes.get(x)).filter(Boolean);
  let h = `<strong>${esc(n.full)}</strong><div class="muted">${n.kind}</div>`;
  if (n.kind === "paper") {
    h += `<p>${esc(n.summary)}</p><div>Domain: ${esc(n.domain)}<br>Difficulty: ${esc(n.difficulty)} · ~${esc(n.timeline_weeks)} weeks<br>Submitted: ${esc(n.submitted)}</div>`;
    h += `<p><a href="${esc(n.pdf_url)}" target="_blank">PDF</a>${n.code_url ? ` · <a href="${esc(n.code_url)}" target="_blank">Code</a>` : ""}</p>`;
    if (n.related?.length) h += `<div><b>Most similar papers</b><ul>${n.related.map(r => `<li><a href="#" data-id="${esc(r[0])}">${esc(nodes.get(r[0])?.full)}</a> (${r[1]})</li>`).join("")}</ul></div>`;
  }
  h += `<div><b>Linked (${nb.length})</b><ul>${nb.map(m => `<li><a href="#" data-id="${esc(m.id)}">${esc(m.full)}</a> <span class="muted">${m.kind}</span></li>`).join("")}</ul></div>`;
  const d = document.getElementById("detail"); d.className = ""; d.innerHTML = h;
  d.querySelectorAll("a[data-id]").forEach(a => a.onclick = e => { e.preventDefault(); focus(a.dataset.id); });
}
function focus(id) { const n = nodes.get(id); if (n && hidden.has(n.kind)) { hidden.delete(n.kind); net.setData({ nodes: new vis.DataView(nodes, { filter: x => !hidden.has(x.kind) }), edges }); } net.selectNodes([id]); net.focus(id, { scale: 1.2, animation: true }); show(id); }
net.on("click", p => p.nodes[0] && show(p.nodes[0]));
net.once("stabilizationIterationsDone", () => net.fit());
document.getElementById("q").addEventListener("keydown", e => {
  if (e.key !== "Enter") return;
  const q = e.target.value.toLowerCase(); const hit = DATA.nodes.find(n => n.full.toLowerCase().includes(q));
  if (hit) focus(hit.id);
});
</script>
</body></html>
"""


def write_html(g: nx.Graph, path: Path, related: dict | None = None) -> None:
    related = related or {}
    nodes = []
    for n, d in g.nodes(data=True):
        kind = d["kind"]
        label = d["label"]
        nodes.append(
            {
                **{k: v for k, v in d.items() if isinstance(v, (str, int, float)) or v is None},
                "id": n,
                "full": label,
                "label": d.get("arxiv_id", label) if kind == "paper" else (label[:28] + "…" if len(label) > 30 else label),
                "title": html.escape(label),
                "color": COLORS.get(kind, "#999"),
                "shape": SHAPES.get(kind, "dot"),
                "size": {"paper": 16, "author": 6}.get(kind, min(8 + 4 * g.degree(n), 24)),
                "related": related.get(n, []),
            }
        )
    edges = [{"from": u, "to": v, "title": d.get("rel", "")} for u, v, d in g.edges(data=True)]
    stats = f"{sum(1 for _, k in g.nodes(data='kind') if k == 'paper')} papers · {g.number_of_nodes()} nodes · {g.number_of_edges()} edges"
    page = (
        TEMPLATE.replace("__DATA__", json.dumps({"nodes": nodes, "edges": edges}).replace("</", "<\\/"))
        .replace("__COLORS__", json.dumps(COLORS))
        .replace("__STATS__", stats)
    )
    path.write_text(page, encoding="utf-8")
