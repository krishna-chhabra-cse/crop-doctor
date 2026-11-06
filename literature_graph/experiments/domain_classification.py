"""Baseline experiment: can the graph recover a paper's research domain?

Leave-one-out: for each paper, forget its domain, then predict it from the
rest of the graph (shared concepts, datasets, authors, arXiv categories).
Domain nodes are removed so no method can read the answer off an edge.
This is the template to copy for new experiments.

    python -m experiments.domain_classification
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict

import networkx as nx
from networkx.algorithms.node_classification import harmonic_function

from graphlab.analyze import SIMILARITY_WEIGHTS, paper_similarity
from graphlab.build import build_graph, nodes_of
from graphlab.experiment import log_metrics, start_run
from graphlab.ingest import load_papers

NO_DOMAIN = {**SIMILARITY_WEIGHTS, "domain": 0.0}


def majority(g, papers, labels, held_out):
    return Counter(labels[p] for p in papers if p != held_out).most_common(1)[0][0]


def knn(k):
    def predict(g, papers, labels, held_out):
        sims = sorted(
            ((paper_similarity(g, held_out, p, NO_DOMAIN), p) for p in papers if p != held_out), reverse=True
        )[:k]
        votes = defaultdict(float)
        for s, p in sims:
            votes[labels[p]] += s
        best = max(votes.items(), key=lambda kv: kv[1])
        # All-zero similarity means the graph has no signal for this paper.
        return best[0] if best[1] > 0 else majority(g, papers, labels, held_out)

    return predict


def label_propagation(g, papers, labels, held_out):
    h = g.copy()
    for p in papers:
        if p != held_out:
            h.nodes[p]["domain_label"] = labels[p]
        else:
            h.nodes[p].pop("domain_label", None)
    # Harmonic function needs the held-out paper connected to some labelled node.
    comp = nx.node_connected_component(h, held_out)
    if not any(p in comp for p in papers if p != held_out):
        return majority(g, papers, labels, held_out)
    sub = h.subgraph(comp).copy()
    preds = harmonic_function(sub, label_name="domain_label")
    return preds[list(sub).index(held_out)]


METHODS = {
    "majority": majority,
    "1nn": knn(1),
    "3nn_weighted": knn(3),
    "label_propagation": label_propagation,
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="data/raw/papers.xlsx")
    args = ap.parse_args()

    full = build_graph(load_papers(args.input))
    papers = nodes_of(full, "paper")
    labels = {p: full.nodes[p]["domain"] for p in papers}
    g = full.copy()
    g.remove_nodes_from(nodes_of(full, "domain"))

    run_dir = start_run("domain_classification", vars(args))
    metrics = {"papers": len(papers), "domains": len(set(labels.values())), "accuracy": {}, "predictions": {}}
    print(f"{len(papers)} papers, {metrics['domains']} domains, leave-one-out")
    print(f"{'method':<20}{'accuracy':>10}")
    for name, method in METHODS.items():
        preds = {p: method(g, papers, labels, p) for p in papers}
        acc = sum(preds[p] == labels[p] for p in papers) / len(papers)
        metrics["accuracy"][name] = round(acc, 4)
        metrics["predictions"][name] = {full.nodes[p]["arxiv_id"]: [labels[p], preds[p]] for p in papers}
        print(f"{name:<20}{acc:>10.3f}")
    log_metrics(run_dir, metrics)
    print(f"Saved to {run_dir}")


if __name__ == "__main__":
    main()
