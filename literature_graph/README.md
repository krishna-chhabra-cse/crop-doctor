# Graph research workbench

Turns a spreadsheet of research papers into a knowledge graph, analyzes it,
and gives you a place to run graph experiments on it.

Seed data: `data/raw/papers.xlsx` (copy of `~/Desktop/healthcare_ml_research_papers.xlsx`, 18 papers).

## Quick start

```bash
pip install -r requirements.txt
python run.py                                  # build + analyze → outputs/
python -m experiments.domain_classification    # baseline experiment
python -m pytest -q
```

Open `outputs/graph.html` in a browser to explore the graph (search, click a node for details,
toggle node kinds). `outputs/report.md` has the written analysis.

## Graph model

| node kind  | from column          | edge from paper |
|------------|----------------------|-----------------|
| `paper`    | one row              | —               |
| `author`   | `authors`            | `written_by`    |
| `concept`  | `key_techniques`     | `uses`          |
| `dataset`  | `datasets_mentioned` (family + named sets like MIMIC, ADNI) | `evaluated_on` |
| `domain`   | `domain`             | `in_domain`     |
| `category` | `categories` (arXiv) | `listed_in`     |

Node ids are `kind:normalized name`, so "Contrastive Learning" and "contrastive learning"
merge into one node.

## Layout

```
graphlab/
  ingest.py      spreadsheet → Paper records (list parsing, dataset extraction)
  build.py       Paper records → networkx graph
  analyze.py     summary, centrality, paper similarity, Louvain clusters, cross-domain bridges
  visualize.py   self-contained interactive HTML (vis-network)
  experiment.py  per-run folders with config.json + metrics.json
experiments/
  domain_classification.py   leave-one-out: predict a paper's domain from the graph
run.py           pipeline entry point
outputs/         generated (git-ignored): graph.html, report.md, analysis.json, graph.graphml, graph.json
```

`graph.graphml` opens in Gephi or Cytoscape. `graph.json` is node-link JSON for D3 or PyG loaders.

## Adding an experiment

Copy `experiments/domain_classification.py`, keep the `start_run` / `log_metrics` calls,
and each run lands in `outputs/experiments/<name>/<timestamp>/`.

## Current findings

- Baseline domain classification is weak (about 17% accuracy for 1-NN, 3-NN and label
  propagation). The hand-tagged `key_techniques` are too sparse: most concepts belong to
  only one paper. The obvious next step is richer node features, such as keywords or
  embeddings from titles and abstracts.
- The cross-domain bridges are Alzheimer's (imaging ↔ mental health), Benchmarking,
  Interpretability and Conformal Prediction.
