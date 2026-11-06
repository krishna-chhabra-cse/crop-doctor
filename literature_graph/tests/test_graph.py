from pathlib import Path

import pytest

from graphlab import analyze
from graphlab.build import build_graph, node_id, nodes_of
from graphlab.ingest import Paper, load_papers, parse_datasets, split_list

DATA = Path(__file__).resolve().parents[1] / "data" / "raw" / "papers.xlsx"


def paper(pid, domain, concepts, authors=(), datasets=()):
    return Paper(pid, f"Paper {pid}", domain, list(authors), list(concepts), list(datasets), [], "High", 8, None, "", "", "")


def test_split_list_ignores_commas_in_parens():
    assert split_list("A, B (x, y), C") == ["A", "B (x, y)", "C"]
    assert split_list(float("nan")) == []


def test_parse_datasets_extracts_named_sets():
    assert parse_datasets("EHR datasets (MIMIC, eICU likely)") == ["EHR datasets", "MIMIC", "eICU"]


def test_same_entity_merges_across_papers():
    g = build_graph([paper("1", "Imaging", ["Contrastive Learning"]), paper("2", "EHR", ["contrastive learning"])])
    assert g.degree(node_id("concept", "Contrastive Learning")) == 2


def test_similarity_and_bridges():
    g = build_graph([
        paper("1", "Imaging", ["CNN", "MRI"], authors=["Ada"]),
        paper("2", "Imaging", ["CNN", "MRI"], authors=["Ada"]),
        paper("3", "EHR", ["Transformers", "MRI"]),
    ])
    p1, p2, p3 = (node_id("paper", i) for i in "123")
    assert analyze.paper_similarity(g, p1, p2) > analyze.paper_similarity(g, p1, p3) > 0
    assert (node_id("concept", "MRI"), ["EHR", "Imaging"]) in analyze.bridges(g)


@pytest.mark.skipif(not DATA.exists(), reason="sample spreadsheet not present")
def test_real_spreadsheet_builds():
    papers = load_papers(DATA)
    g = build_graph(papers)
    assert len(nodes_of(g, "paper")) == len(papers) > 0
    assert all(g.degree(p) > 0 for p in nodes_of(g, "paper"))
