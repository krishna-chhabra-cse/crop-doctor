"""Tests for the data preparation step, on a tiny fake dataset built in a temp folder."""
from __future__ import annotations

from pathlib import Path

from PIL import Image

from crop_doctor.data.prepare import drop_duplicates, scan, split

CLASS_MAP = {
    "a_disease": ("PV_A", "PD A"),
    "b_disease": ("PV_B", "PD B"),
    "rare": ("PV_R", "PD R"),
}


def _img(path: Path, color: tuple[int, int, int], size: int = 64) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (size, size), color).save(path)


def _fake_datasets(root: Path) -> tuple[Path, Path]:
    pv, pd_ = root / "plantvillage", root / "plantdoc"
    for ci, (pv_name, pd_name) in enumerate(v for v in CLASS_MAP.values()):
        for i in range(20):  # lab photos: unique colours
            _img(pv / "raw" / "color" / pv_name / f"{i}.jpg", (ci * 80, i * 10, 5))
        n_field = 2 if pv_name == "PV_R" else 20  # "rare" has too few field photos
        for i in range(n_field):
            split_dir = "train" if i % 2 else "test"
            _img(pd_ / split_dir / pd_name / f"{i}.png", (ci * 80, i * 10, 200))
    # A corrupt file, a tiny file, and a duplicate across PlantDoc train/test.
    (pd_ / "train" / "PD A" / "broken.jpg").write_bytes(b"not an image")
    _img(pd_ / "train" / "PD A" / "tiny.png", (1, 2, 3), size=8)
    _img(pd_ / "test" / "PD A" / "dup.png", (0, 10, 200))  # same pixels as train/PD A/1.png
    return pv, pd_


def test_full_pipeline(tmp_path: Path) -> None:
    pv, pd_ = _fake_datasets(tmp_path)
    res = scan(CLASS_MAP, pv, pd_, tmp_path)
    reasons = {d["reason"].split(":")[0] for d in res.dropped}
    assert {"unreadable", "too small"} <= reasons

    df = drop_duplicates(res.df, res.dropped)
    assert df["md5"].is_unique
    assert any(d["reason"] == "exact duplicate" for d in res.dropped)

    df, kept, removed = split(df, min_field=15, seed=0)
    assert removed == ["rare"] and kept == ["a_disease", "b_disease"]
    assert set(df["split"]) == {"lab_train", "lab_val", "lab_test", "field_pool", "field_test"}

    # Lab and field photos never mix, and no image is in two splits.
    assert set(df[df["source"] == "plantvillage"]["split"]) == {"lab_train", "lab_val", "lab_test"}
    assert set(df[df["source"] == "plantdoc"]["split"]) == {"field_pool", "field_test"}
    assert df["path"].is_unique

    # Stratified: every kept class appears in every split.
    for _, part in df.groupby("split"):
        assert set(part["label"]) == set(kept)

    # Same seed -> identical splits (reproducibility).
    df2, _, _ = split(drop_duplicates(scan(CLASS_MAP, pv, pd_, tmp_path).df, []), min_field=15, seed=0)
    assert df[["path", "split"]].equals(df2[["path", "split"]])
