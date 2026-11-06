"""Tiny experiment harness: each run gets its own folder with config and metrics."""
from __future__ import annotations

import json
import time
from pathlib import Path


def start_run(name: str, config: dict, root: str | Path = "outputs/experiments") -> Path:
    run_dir = Path(root) / name / time.strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    return run_dir


def log_metrics(run_dir: Path, metrics: dict) -> None:
    (run_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
