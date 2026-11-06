"""Graph analyses: structure, central entities, paper similarity, clusters, bridges."""
from __future__ import annotations

from collections import Counter

import networkx as nx

from .build import nodes_of

# How much overlap in each kind of entity says about two papers being related.
SIMILARITY_WEIGHTS = {"concept": 1.0, "dataset": 1.0, "domain": 1.0, "author": 0.5, "category": 0.25}


def summary(g: nx.Graph) -> dict:
    return {
        "nodes": g.number_of_nodes(),
        "edges": g.number_of_edges(),
        "components": nx.number_connected_components(g),
        "density": round(nx.density(g), 4),
        "nodes_by_kind": dict(Counter(k for _, k in g.nodes(data="kind"))),
        "edges_by_relation": dict(Counter(r for *_, r in g.edges(data="rel"))),
    }


def paper_similarity(g: nx.Graph, a: str, b: str, weights: dict | None = None) -> float:
    """Weighted mean of per-kind Jaccard overlap, over kinds either paper has.

    Scoring each kind separately stops long author lists (rarely shared) from
    drowning out shared concepts and datasets.
    """
    weights = SIMILARITY_WEIGHTS if weights is None else weights
    total = score = 0.0
    for kind, w in weights.items():
        na = {n for n in g[a] if g.nodes[n]["kind"] == kind}
        nb = {n for n in g[b] if g.nodes[n]["kind"] == kind}
        if w and (na or nb):
            total += w
            score += w * len(na & nb) / len(na | nb)
    return score / total if total else 0.0


def paper_projection(g: nx.Graph, min_similarity: float = 0.0) -> nx.Graph:
    papers = nodes_of(g, "paper")
    p = nx.Graph()
    p.add_nodes_from((n, g.nodes[n]) for n in papers)
    for i, a in enumerate(papers):
        for b in papers[i + 1 :]:
            s = paper_similarity(g, a, b)
            if s > min_similarity:
                p.add_edge(a, b, weight=round(s, 4))
    return p


def related_papers(g: nx.Graph, k: int = 3) -> dict[str, list[tuple[str, float]]]:
    proj = paper_projection(g)
    out = {}
    for n in proj:
        ranked = sorted(proj[n].items(), key=lambda kv: kv[1]["weight"], reverse=True)[:k]
        out[n] = [(m, d["weight"]) for m, d in ranked]
    return out


def clusters(g: nx.Graph, seed: int = 0) -> list[list[str]]:
    proj = paper_projection(g)
    comms = nx.community.louvain_communities(proj, weight="weight", seed=seed)
    return sorted((sorted(c) for c in comms), key=len, reverse=True)


def central_entities(g: nx.Graph, kind: str, top: int = 10) -> list[tuple[str, int, float]]:
    """Entities of one kind ranked by paper count, with betweenness as a tiebreaker."""
    btw = nx.betweenness_centrality(g, seed=0, k=min(200, len(g)))
    rows = [(n, g.degree(n), round(btw[n], 4)) for n in nodes_of(g, kind)]
    return sorted(rows, key=lambda r: (r[1], r[2]), reverse=True)[:top]


def bridges(g: nx.Graph) -> list[tuple[str, list[str]]]:
    """Concepts and datasets used by papers in more than one domain."""
    out = []
    for n, kind in g.nodes(data="kind"):
        if kind not in ("concept", "dataset"):
            continue
        domains = sorted({g.nodes[p]["domain"] for p in g[n] if g.nodes[p]["kind"] == "paper"})
        if len(domains) > 1:
            out.append((n, domains))
    return sorted(out, key=lambda r: len(r[1]), reverse=True)
