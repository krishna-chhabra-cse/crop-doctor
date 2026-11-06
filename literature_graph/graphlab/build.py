"""Turn paper records into a heterogeneous research graph.

Node ids are "<kind>:<normalized name>" so the same concept, author or dataset
mentioned by different papers collapses into one node.
"""
from __future__ import annotations

import re

import networkx as nx

from .ingest import Paper

# Relation name for each kind of node a paper links to.
RELATIONS = {
    "author": "written_by",
    "concept": "uses",
    "dataset": "evaluated_on",
    "domain": "in_domain",
    "category": "listed_in",
}


def node_id(kind: str, name: str) -> str:
    key = re.sub(r"[^a-z0-9]+", " ", name.lower().replace("'", "")).strip()
    return f"{kind}:{key}"


def build_graph(papers: list[Paper]) -> nx.Graph:
    g = nx.Graph()
    for p in papers:
        pid = node_id("paper", p.arxiv_id)
        g.add_node(
            pid,
            kind="paper",
            label=p.title,
            arxiv_id=p.arxiv_id,
            domain=p.domain,
            difficulty=p.difficulty,
            timeline_weeks=p.timeline_weeks or 0,  # GraphML can't store None
            code_url=p.code_url or "",
            submitted=p.submitted,
            pdf_url=p.pdf_url,
            summary=p.summary,
        )
        links = {
            "author": p.authors,
            "concept": p.concepts,
            "dataset": p.datasets,
            "domain": [p.domain],
            "category": p.categories,
        }
        for kind, names in links.items():
            for name in names:
                nid = node_id(kind, name)
                if nid not in g:
                    g.add_node(nid, kind=kind, label=name)
                g.add_edge(pid, nid, rel=RELATIONS[kind])
    return g


def nodes_of(g: nx.Graph, kind: str) -> list[str]:
    return [n for n, k in g.nodes(data="kind") if k == kind]
