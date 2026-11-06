"""Turn the raw downloads into fixed, reproducible train/val/test splits.

    python -m crop_doctor.data.prepare

Steps
1. Find every image of our shared classes in PlantVillage (lab) and PlantDoc (field).
2. Drop unreadable/tiny files and exact duplicates (same bytes = same MD5 hash).
   PlantDoc is known to contain duplicates, and a duplicate shared between the
   calibration pool and the test set would leak the answer.
3. Drop classes with too few field photos (config.MIN_FIELD_IMAGES).
4. Split, stratified by class with a fixed seed:
     PlantVillage -> lab_train 80% / lab_val 10% / lab_test 10%
     PlantDoc     -> field_pool 50% (plays the "expert labels") / field_test 50% (never touched for fitting)
5. Save one CSV per split + classes.json + a class-count table.

The CSVs are small and are the official definition of the dataset: every later
experiment reads them, so everyone on the team gets exactly the same splits.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from PIL import Image
from sklearn.model_selection import train_test_split

from crop_doctor import config

MIN_SIDE_PX = 32


@dataclass
class ScanResult:
    df: pd.DataFrame          # columns: path, label, source, md5, width, height
    dropped: list[dict]       # files we rejected and why


def _image_files(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in config.IMAGE_EXTS)


def _inspect(path: Path) -> tuple[str, int, int]:
    """Return (md5, width, height); raises if the file is not a readable image."""
    data = path.read_bytes()
    with Image.open(path) as im:
        im.verify()  # detects truncated/corrupt files
    with Image.open(path) as im:
        w, h = im.size
    return hashlib.md5(data).hexdigest(), w, h


def scan(class_map: dict[str, tuple[str, str]], pv_dir: Path, pd_dir: Path, datasets_dir: Path) -> ScanResult:
    rows, dropped = [], []
    for label, (pv_name, pd_name) in class_map.items():
        sources = [("plantvillage", pv_dir / "raw" / "color" / pv_name)]
        sources += [("plantdoc", pd_dir / split / pd_name) for split in ("train", "test")]
        for source, folder in sources:
            for f in _image_files(folder):
                rel = f.relative_to(datasets_dir).as_posix()
                try:
                    md5, w, h = _inspect(f)
                except Exception as e:  # noqa: BLE001 - any failure means unusable image
                    dropped.append({"path": rel, "reason": f"unreadable: {type(e).__name__}"})
                    continue
                if min(w, h) < MIN_SIDE_PX:
                    dropped.append({"path": rel, "reason": f"too small: {w}x{h}"})
                    continue
                rows.append({"path": rel, "label": label, "source": source, "md5": md5, "width": w, "height": h})
    return ScanResult(pd.DataFrame(rows, columns=["path", "label", "source", "md5", "width", "height"]), dropped)


def drop_duplicates(df: pd.DataFrame, dropped: list[dict]) -> pd.DataFrame:
    """Keep one copy of each identical file.

    If the same image appears under two different labels we cannot know which is
    right, so every copy of it is removed.
    """
    labels_per_hash = df.groupby("md5")["label"].nunique()
    conflicting = set(labels_per_hash[labels_per_hash > 1].index)
    for _, r in df[df["md5"].isin(conflicting)].iterrows():
        dropped.append({"path": r["path"], "reason": "duplicate with conflicting labels"})
    df = df[~df["md5"].isin(conflicting)]

    # Prefer keeping the PlantVillage copy if a field photo is byte-identical to a lab photo
    # (it then can't count as an unseen field photo).
    df = df.assign(_rank=(df["source"] == "plantdoc").astype(int)).sort_values(["md5", "_rank", "path"])
    df = df.drop(columns="_rank")
    dup_mask = df.duplicated("md5", keep="first")
    for _, r in df[dup_mask].iterrows():
        dropped.append({"path": r["path"], "reason": "exact duplicate"})
    return df[~dup_mask].sort_values("path").reset_index(drop=True)


def split(df: pd.DataFrame, min_field: int, seed: int) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Add a `split` column. Returns (df, kept_classes, removed_classes)."""
    field_counts = df[df["source"] == "plantdoc"]["label"].value_counts()
    lab_counts = df[df["source"] == "plantvillage"]["label"].value_counts()
    all_labels = sorted(df["label"].unique())
    kept = [c for c in all_labels if field_counts.get(c, 0) >= min_field and lab_counts.get(c, 0) >= 10]
    removed = [c for c in all_labels if c not in kept]
    if not kept:
        raise SystemExit("No class has enough lab AND field photos. Is the PlantDoc download complete?")
    df = df[df["label"].isin(kept)].copy()

    lab = df[df["source"] == "plantvillage"]
    field = df[df["source"] == "plantdoc"]

    val_test = config.LAB_SPLIT["lab_val"] + config.LAB_SPLIT["lab_test"]
    lab_train, lab_rest = train_test_split(lab, test_size=val_test, stratify=lab["label"], random_state=seed)
    test_share = config.LAB_SPLIT["lab_test"] / val_test
    lab_val, lab_test = train_test_split(lab_rest, test_size=test_share, stratify=lab_rest["label"], random_state=seed)
    field_pool, field_test = train_test_split(
        field, train_size=config.FIELD_POOL_FRACTION, stratify=field["label"], random_state=seed
    )

    parts = {"lab_train": lab_train, "lab_val": lab_val, "lab_test": lab_test,
             "field_pool": field_pool, "field_test": field_test}
    for name, part in parts.items():
        df.loc[part.index, "split"] = name
    label_idx = {c: i for i, c in enumerate(kept)}
    df["label_idx"] = df["label"].map(label_idx)
    return df.sort_values(["split", "path"]).reset_index(drop=True), kept, removed


def count_table(df: pd.DataFrame) -> pd.DataFrame:
    t = df.pivot_table(index="label", columns="split", values="path", aggfunc="count", fill_value=0)
    order = [c for c in ["lab_train", "lab_val", "lab_test", "field_pool", "field_test"] if c in t.columns]
    t = t[order]
    t.loc["TOTAL"] = t.sum()
    return t


def main() -> None:
    if not config.PLANTVILLAGE_DIR.exists() or not config.PLANTDOC_DIR.exists():
        raise SystemExit("Datasets missing. Run: python -m crop_doctor.data.download")

    print("Scanning and checking images ...")
    res = scan(config.CLASS_MAP, config.PLANTVILLAGE_DIR, config.PLANTDOC_DIR, config.DATASETS_DIR)
    print(f"  readable images: {len(res.df)}  rejected: {len(res.dropped)}")
    df = drop_duplicates(res.df, res.dropped)
    print(f"  after removing duplicates: {len(df)}")

    df, kept, removed = split(df, config.MIN_FIELD_IMAGES, config.SEED)
    if removed:
        print(f"  classes removed (fewer than {config.MIN_FIELD_IMAGES} field photos): {removed}")

    config.SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    cols = ["path", "label", "label_idx", "source", "md5", "width", "height"]
    for name, part in df.groupby("split"):
        part[cols].to_csv(config.SPLITS_DIR / f"{name}.csv", index=False)
    (config.SPLITS_DIR / "classes.json").write_text(json.dumps(kept, indent=2))
    pd.DataFrame(res.dropped, columns=["path", "reason"]).to_csv(config.OUTPUTS_DIR / "dropped_images.csv", index=False)

    table = count_table(df)
    table.to_csv(config.OUTPUTS_DIR / "class_counts.csv")
    print("\nImages per class and split:\n")
    print(table.to_string())
    print(f"\nSaved splits to {config.SPLITS_DIR}")


if __name__ == "__main__":
    main()
