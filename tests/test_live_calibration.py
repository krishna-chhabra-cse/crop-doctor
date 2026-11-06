"""Live recalibration rules, tested with a fake model and synthetic logits (no GPU, temp database)."""
from __future__ import annotations

import numpy as np
import pytest

from crop_doctor.app import db
from crop_doctor.assistant import live_calibration as lc
from crop_doctor.uncertainty.calibration import softmax

CLASSES = ["potato_a", "potato_b", "tomato_a", "tomato_b", "tomato_c"]


class FakeDoctor:
    classes = CLASSES

    def __init__(self):
        self.temperature, self.qhat = 1.0, 0.9

    def set_calibration(self, t, q):
        self.temperature, self.qhat = t, q


def _split(n, rng, confident):
    """Lab-like (confident and right) or field-like (unsure) synthetic logits."""
    y = rng.integers(2, 5, n)                       # tomato classes
    lg = rng.normal(0, 1, (n, 5))
    lg[np.arange(n), y] += 6 if confident else 1.0
    lg[:, :2] = -np.inf                             # crop mask: tomato photos
    return lg, y


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    rng = np.random.default_rng(0)
    data = {"lab_val": _split(400, rng, True), "final_field_cal": _split(60, rng, False),
            "final_field_val": _split(80, rng, False), "field_test": _split(300, rng, False)}
    monkeypatch.setattr(lc, "split_logits", lambda split, doctor: data[split])
    return FakeDoctor()


def test_field_points_replace_lab_points(env):
    run = lc.reset(env, "lab")
    assert run["n_field_points"] == 0 and run["n_points"] == 400
    lab_cov = run["monitor_coverage"]
    run = lc.simulate_expert_labels(env, 30, seed=1)
    assert run["n_points"] == 30 and run["n_field_points"] == 30        # lab points no longer used
    assert run["monitor_coverage"] > lab_cov                            # field labels restore coverage


def test_too_few_field_labels_means_every_disease_possible(env):
    lc.reset(env, "lab")
    run = lc.simulate_expert_labels(env, 5, seed=2)
    assert run["qhat"] == float("inf") and env.qhat == float("inf")
    assert run["monitor_coverage"] == 1.0


def test_simulated_labels_are_not_reused(env):
    lc.reset(env, "lab")
    for s in range(10):
        lc.simulate_expert_labels(env, 10, seed=s)
    sims = [p for p in db.calibration_points() if p["source"] == "simulated_expert"]
    assert len(sims) == 80                                              # pool has 80 photos, never duplicated


def test_only_audit_cases_join_calibration(env):
    lc.reset(env, "field")
    n = len(db.calibration_points())
    assert lc.add_expert_label(env, {"audit": 0, "id": 1}, "tomato_a") is None
    assert lc.add_expert_label(env, {"audit": 1, "id": 2}, "not_a_class") is None
    assert len(db.calibration_points()) == n


def test_runs_are_logged_and_reapplied(env):
    lc.reset(env, "field")
    lc.simulate_expert_labels(env, 20, seed=3)
    runs = db.calibration_runs()
    assert len(runs) == 2 and runs[-1]["n_field_points"] == 80
    env.set_calibration(1.0, 0.1)
    lc.ensure_initialised(env)
    assert env.qhat == pytest.approx(runs[-1]["qhat"])
    assert np.isfinite(softmax(np.array([[1.0, 2.0, -np.inf]]), env.temperature)).all()
