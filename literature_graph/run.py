"""Build the research graph, analyze it, and write every output.

    python run.py                          # uses data/raw/papers.xlsx
    python run.py --input other.xlsx --out outputs/other
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import networkx as nx

from graphlab import analyze
from graphlab.build import build_graph
from graphlab.ingest import load_papers
from graphlab.visualize import write_html


def label(g: nx.Graph, n: str) -> str:
    return g.nodes[n]["label"]


def write_report(g: nx.Graph, out: Path) -> dict:
    stats = analyze.summary(g)
    related = analyze.related_papers(g, k=3)
    groups = analyze.clusters(g)
    bridges = analyze.bridges(g)
    top_concepts = analyze.central_entities(g, "concept")
    top_datasets = analyze.central_entities(g, "dataset", top=5)

    lines = ["# Research graph report", ""]
    lines += [f"- **{k.replace('_', ' ')}**: {v}" for k, v in stats.items()]
    lines += ["", "## Most connected concepts", "", "| concept | papers | betweenness |", "|---|---|---|"]
    lines += [f"| {label(g, n)} | {d} | {b} |" for n, d, b in top_concepts]
    lines += ["", "## Most used datasets", "", "| dataset | papers | betweenness |", "|---|---|---|"]
    lines += [f"| {label(g, n)} | {d} | {b} |" for n, d, b in top_datasets]
    lines += ["", "## Cross-domain bridges", ""]
    lines += [f"- **{label(g, n)}** links {', '.join(ds)}" for n, ds in bridges] or ["- none found"]
    lines += ["", "## Paper clusters (Louvain on paper similarity)", ""]
    for i, group in enumerate(groups, 1):
        lines.append(f"### Cluster {i} ({len(group)} papers)")
        lines += [f"- {label(g, p)} _({g.nodes[p]['domain']})_" for p in group]
        lines.append("")
    lines += ["## Related papers", ""]
    for p, rel in related.items():
        lines.append(f"- **{label(g, p)}**")
        lines += [f"  - {label(g, q)} (similarity {s})" for q, s in rel]
    (out / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    data = {
        "summary": stats,
        "top_concepts": top_concepts,
        "top_datasets": top_datasets,
        "bridges": bridges,
        "clusters": groups,
        "related": related,
    }
    (out / "analysis.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", default="data/raw/papers.xlsx")
    ap.add_argument("--out", default="outputs")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    g = build_graph(load_papers(args.input))

    nx.write_graphml(g, out / "graph.graphml")
    (out / "graph.json").write_text(json.dumps(nx.node_link_data(g, edges="links"), indent=2), encoding="utf-8")
    data = write_report(g, out)
    write_html(g, out / "graph.html", related=data["related"])

    s = data["summary"]
    print(f"Built graph: {s['nodes']} nodes, {s['edges']} edges, {s['components']} component(s)")
    print("  " + ", ".join(f"{k}: {v}" for k, v in s["nodes_by_kind"].items()))
    print(f"Wrote {out}/graph.html, report.md, analysis.json, graph.graphml, graph.json")


if __name__ == "__main__":
    main()
