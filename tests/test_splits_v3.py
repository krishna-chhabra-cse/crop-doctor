"""Exp 10 splits (crop_doctor/data/splits_v3): unknown problems are split by DISEASE, and nothing leaks."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from crop_doctor.data.prepare_v3 import HELD_OUT, OTHER, TAUGHT

ROOT = Path(__file__).resolve().parents[1] / "crop_doctor" / "data"
V2, V3 = ROOT / "splits_v2", ROOT / "splits_v3"


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(V3 / f"{name}.csv")


def test_v2_classes_keep_their_index_and_something_else_is_last():
    v2 = json.loads((V2 / "classes.json").read_text())
    v3 = json.loads((V3 / "classes.json").read_text())
    assert v3[:-1] == v2 and v3[-1] == OTHER and OTHER.startswith("tomato_")   # tomato-only via crop masking


def test_unknown_problems_are_split_by_disease_never_by_photo():
    assert not set(TAUGHT) & set(HELD_OUT)
    taught = pd.concat([read("other_train"), read("other_val")])
    held = read("unknown_heldout")
    assert set(taught["disease"]) == set(TAUGHT)
    assert set(held["disease"]) == set(HELD_OUT)
    assert not set(taught["path"]) & set(held["path"])
    assert not set(taught["md5"]) & set(held["md5"])
    assert (taught["label"] == OTHER).all()


def test_no_photo_is_in_two_splits():
    names = ["lab_train", "lab_val", "lab_test", "field_train", "field_val", "field_cal", "field_test",
             "other_train", "other_val", "tv_known_holdout", "unknown_heldout"]
    paths = pd.concat([read(n)["path"] for n in names])
    assert paths.is_unique


def test_known_tomato_village_check_photos_were_never_trained_on():
    hold = read("tv_known_holdout")
    assert (hold["source"] == "tomato_village").all() and len(hold) > 100
    assert not set(hold["path"]) & set(read("field_train")["path"])
    # Everything else in v3 field_train is exactly v2's field_train.
    v2_train = set(pd.read_csv(V2 / "field_train.csv")["path"])
    assert set(read("field_train")["path"]) | set(hold["path"]) == v2_train


def test_known_test_and_calibration_sets_are_unchanged_from_v2():
    for name in ("field_val", "field_cal", "field_test"):
        assert read(name).equals(pd.read_csv(V2 / f"{name}.csv"))
