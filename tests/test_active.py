import numpy as np
import pytest

from crop_doctor.uncertainty.active import entropy, pick_for_labelling, split_pool


def test_split_pool_is_disjoint_and_complete():
    pick, cal = split_pool(100, 20, seed=1)
    assert len(cal) == 20 and not set(pick) & set(cal)
    assert sorted([*pick, *cal]) == list(range(100))


def test_entropy_is_higher_when_unsure():
    h = entropy(np.array([[0.98, 0.01, 0.01], [1 / 3, 1 / 3, 1 / 3]]))
    assert h[1] > h[0]


def test_uncertain_picks_least_sure_candidates_only():
    probs = np.array([[0.5, 0.5], [0.99, 0.01], [0.6, 0.4], [0.5, 0.5], [0.9, 0.1]])
    # Photo 3 is the most uncertain overall, but it is reserved for calibration.
    picked = pick_for_labelling("uncertain", probs, np.array([0, 1, 2, 4]), 2, seed=0)
    assert set(picked) == {0, 2}


def test_random_pick_is_distinct_reproducible_and_inside_candidates():
    probs = np.full((50, 2), 0.5)
    candidates = np.arange(10, 50)
    a = pick_for_labelling("random", probs, candidates, 15, seed=3)
    assert len(set(a)) == 15 and set(a) <= set(candidates)
    assert (a == pick_for_labelling("random", probs, candidates, 15, seed=3)).all()


def test_rejects_bad_inputs():
    probs = np.full((3, 2), 0.5)
    with pytest.raises(ValueError):
        pick_for_labelling("clever", probs, np.arange(3), 1, seed=0)
    with pytest.raises(ValueError):
        pick_for_labelling("random", probs, np.arange(3), 4, seed=0)
