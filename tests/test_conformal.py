"""Conformal prediction: check the maths and the 90% guarantee on synthetic data."""
from __future__ import annotations

import math

import numpy as np

from crop_doctor.uncertainty.calibration import softmax
from crop_doctor.uncertainty.conformal import (
    aps_scores, class_coverage, conformal_quantile, evaluate_sets, prediction_sets, uniform_noise,
)


def test_aps_score_and_sets_by_hand():
    probs = np.array([[0.6, 0.3, 0.1]])
    assert np.allclose(aps_scores(probs, np.array([0])), [0.6])
    assert np.allclose(aps_scores(probs, np.array([1])), [0.9])
    assert np.allclose(aps_scores(probs, np.array([2])), [1.0])
    # q-hat 0.7: mass above class 0 = 0 < .7 (in), above class 1 = .6 < .7 (in), above class 2 = .9 (out)
    assert prediction_sets(probs, 0.7).tolist() == [[True, True, False]]
    assert prediction_sets(probs, 0.05).tolist() == [[True, False, False]]  # never empty


def test_quantile_finite_sample_rule():
    scores = np.arange(1, 11) / 10  # 0.1 ... 1.0, n = 10
    assert conformal_quantile(scores, 0.1) == 1.0          # ceil(11 * 0.9) = 10th smallest
    assert conformal_quantile(scores[:8], 0.1) == math.inf  # n = 8: too few photos for 90%


def _synthetic(n, k, rng):
    logits = rng.normal(0, 1.2, (n, k))
    probs = softmax(logits)
    labels = np.array([rng.choice(k, p=p) for p in probs])  # labels drawn from the model's own beliefs
    return probs, labels


def test_coverage_guarantee_holds_on_exchangeable_data():
    rng = np.random.default_rng(1)
    covs, covs_rand = [], []
    for i in range(30):
        cal_p, cal_y = _synthetic(200, 6, rng)
        test_p, test_y = _synthetic(500, 6, rng)
        q = conformal_quantile(aps_scores(cal_p, cal_y), 0.1)
        covs.append(evaluate_sets(prediction_sets(test_p, q), test_y)["coverage"])
        u_cal, u_test = uniform_noise(200, i), uniform_noise(500, 100 + i)
        qr = conformal_quantile(aps_scores(cal_p, cal_y, u_cal), 0.1)
        covs_rand.append(evaluate_sets(prediction_sets(test_p, qr, u_test), test_y)["coverage"])
    assert np.mean(covs) >= 0.89
    assert 0.88 <= np.mean(covs_rand) <= 0.93  # randomised APS: close to exactly 90%


def test_randomised_aps_mirrors_its_score():
    # The true class is in the set exactly when its score <= q-hat.
    rng = np.random.default_rng(3)
    p, y = _synthetic(300, 5, rng)
    u = uniform_noise(300, 7)
    s = aps_scores(p, y, u)
    for q in (0.3, 0.6, 0.9):
        covered = prediction_sets(p, q, u)[np.arange(300), y]
        assert (covered == (s <= q)).all()


def test_overconfident_calibration_gives_small_sets_with_randomisation():
    # A model ~99.9% sure and right on calibration photos: plain APS gives q-hat ~ 0.999,
    # randomised APS gives q-hat ~ 0.9, so a field photo gets a short list instead of every class.
    cal = np.tile([0.999, 0.0005, 0.0005], (100, 1))
    y = np.zeros(100, dtype=int)
    assert conformal_quantile(aps_scores(cal, y), 0.1) > 0.99
    assert conformal_quantile(aps_scores(cal, y, uniform_noise(100, 0)), 0.1) < 0.95


def test_evaluate_and_class_coverage():
    sets = np.array([[True, False], [True, True], [False, True]])
    labels = np.array([0, 1, 0])
    r = evaluate_sets(sets, labels)
    assert r["coverage"] == 2 / 3 and r["avg_set_size"] == 4 / 3
    assert r["answered_rate"] == 2 / 3 and r["answered_accuracy"] == 0.5
    assert np.allclose(class_coverage(sets, labels, 2), [0.5, 1.0])
