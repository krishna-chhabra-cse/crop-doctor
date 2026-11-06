"""Sanity checks for calibration and selective-prediction maths on hand-made examples."""
from __future__ import annotations

import numpy as np

from crop_doctor.uncertainty.calibration import ece, fit_temperature, nll, softmax
from crop_doctor.uncertainty.selective import (
    apply_threshold, aurc, oracle_aurc, risk_at_coverage, risk_coverage, threshold_for_risk,
)


def test_softmax_rows_sum_to_one_and_temperature_keeps_prediction():
    logits = np.array([[2.0, 1.0, 0.0], [0.0, 5.0, 1.0]])
    for t in (0.5, 1.0, 3.0):
        p = softmax(logits, t)
        assert np.allclose(p.sum(1), 1)
        assert (p.argmax(1) == logits.argmax(1)).all()
    assert softmax(logits, 3.0).max(1)[0] < softmax(logits, 1.0).max(1)[0]  # higher T = less confident


def test_ece_zero_when_confidence_matches_accuracy():
    # 10 predictions at 80% confidence, 8 correct -> perfectly calibrated.
    probs = np.tile([0.8, 0.2], (10, 1))
    labels = np.array([0] * 8 + [1] * 2)
    assert ece(probs, labels) < 1e-9


def test_ece_large_when_overconfident():
    probs = np.tile([0.99, 0.01], (10, 1))
    labels = np.array([0] * 5 + [1] * 5)  # 99% confident, 50% right
    assert abs(ece(probs, labels) - 0.49) < 1e-9


def test_temperature_scaling_fixes_an_overconfident_model():
    rng = np.random.default_rng(0)
    n, k = 4000, 5
    labels = rng.integers(0, k, n)
    true_logits = rng.normal(0, 1, (n, k))
    true_logits[np.arange(n), labels] += 1.5
    # Sample labels from the "honest" probabilities, then make the model 4x overconfident.
    honest = softmax(true_logits)
    labels = np.array([rng.choice(k, p=p) for p in honest])
    over = true_logits * 4
    t = fit_temperature(over, labels)
    assert 3.0 < t < 5.0
    assert ece(softmax(over, t), labels) < ece(softmax(over), labels)
    assert nll(softmax(over, t), labels) < nll(softmax(over), labels)


def test_risk_coverage_and_aurc():
    conf = np.array([0.9, 0.8, 0.7, 0.6])
    correct = np.array([True, True, False, False])
    cov, risk = risk_coverage(conf, correct)
    assert np.allclose(cov, [0.25, 0.5, 0.75, 1.0])
    assert np.allclose(risk, [0, 0, 1 / 3, 0.5])
    assert aurc(conf, correct) == oracle_aurc(correct)  # perfect ranking here
    assert risk_at_coverage(conf, correct, 0.5) == 0
    # Reverse ranking is the worst case.
    assert aurc(-conf, correct) > aurc(conf, correct)


def test_threshold_for_risk():
    conf = np.array([0.95, 0.9, 0.85, 0.6, 0.5])
    correct = np.array([True, True, True, False, True])
    th = threshold_for_risk(conf, correct, 0.0)
    assert th == 0.85
    res = apply_threshold(conf, correct, th)
    assert res["coverage"] == 0.6 and res["risk"] == 0.0
