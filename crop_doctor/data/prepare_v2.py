"""Build the v2 dataset: more field photos and a new class (healthy potato).

    python -m crop_doctor.data.prepare_v2

The original splits (crop_doctor/data/splits/, Days 1-5) are NOT changed, so the research results stay valid.
v2 writes crop_doctor/data/splits_v2/.

Sources and how each is used:
  PlantVillage (lab)          lab_train / lab_val / lab_test, now including Potato___healthy (11 classes)
  PlantDoc (web field)        same assignment as before: train 285 / val 95 / cal 95 / test 476
  Tanzania potato (CC-BY-4.0) smartphone photos from smallholder farms (Zenodo 10.5281/zenodo.8286529):
                              per class 1200 train / 150 val / 150 cal / 300 test, drawn at random
  Tomato-Village (2023)       Indian leaves photographed on paper (not in the field) and with rotated copies,
                              so TRAINING ONLY; its other diseases form an "unknown disease" probe set

Checks: unreadable files dropped; exact duplicates (MD5) removed across ALL sources; and for Tanzania, a
perceptual-hash check that no test photo has a near-identical twin in train.
"""
from __future__ import annotations

import hashlib
import io
import json
import random
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.model_selection import train_test_split

from crop_doctor import config

OUT = config.ROOT / "crop_doctor" / "data" / "splits_v2"
TZ_DIR = config.DATASETS_DIR / "tanzania_potato"
TZ_IMAGES = TZ_DIR / "images"
TV_DIR = config.DATASETS_DIR / "tomato_village" / "Variant-a(Multiclass Classification)"
TZ_CLASSES = {"healthy": "potato_healthy", "earlyblt": "potato_early_blight", "lateblt": "potato_late_blight"}
TZ_COUNTS = {"train": 1200, "val": 150, "cal": 150, "test": 300}
TV_CLASSES = {"Early_blight": "tomato_early_blight", "Late_blight": "tomato_late_blight", "Healthy": "tomato_healthy"}
TV_UNKNOWN = ["Leaf Miner", "Spotted Wilt Virus", "Magnesium Deficiency", "Nitrogen Deficiency", "Pottassium Deficiency"]
V2_CLASSES = sorted(list(json.loads((config.SPLITS_DIR / "classes.json").read_text())) + ["potato_healthy"])


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def dhash(path: Path, n: int = 8) -> np.ndarray:
    with Image.open(path) as im:
        a = np.asarray(im.convert("L").resize((n + 1, n)), dtype=np.int16)
    return (a[:, 1:] > a[:, :-1]).ravel()


def extract_tanzania(seed: int) -> pd.DataFrame:
    """Pick photos at random from each zip and save them shrunk to 512 px (we train at 224 px)."""
    rows = []
    need = sum(TZ_COUNTS.values()) + 100       # spare photos to replace any rejected ones
    for zname, label in TZ_CLASSES.items():
        z = zipfile.ZipFile(TZ_DIR / "zips" / f"{zname}.zip")
        # The zips contain MANY exact copies (early blight: only 35% unique; one photo appears 350 times).
        # Remove copies first (same CRC32 checksum + same size = same file), THEN sample.
        unique = {}
        for info in sorted(z.infolist(), key=lambda i: i.filename):
            if re.fullmatch(rf"{zname}/{zname}\d+\.jpg", info.filename):
                unique.setdefault((info.CRC, info.file_size), info.filename)
        names = sorted(unique.values())
        pick = random.Random(seed).sample(names, need)
        (TZ_IMAGES / zname).mkdir(parents=True, exist_ok=True)
        for n in pick:
            out = TZ_IMAGES / zname / Path(n).name
            if not out.exists():
                try:
                    im = Image.open(io.BytesIO(z.read(n))).convert("RGB")
                    im.thumbnail((512, 512))
                    im.save(out, quality=92)
                except Exception:  # noqa: BLE001 - corrupt photo: skip it
                    continue
            rows.append({"path": out.relative_to(config.DATASETS_DIR).as_posix(), "label": label, "source": "tanzania"})
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    label_idx = {c: i for i, c in enumerate(V2_CLASSES)}

    # Lab: reuse v1 splits, add Potato___healthy split 80/10/10.
    frames = []
    for split in ("lab_train", "lab_val", "lab_test"):
        frames.append(pd.read_csv(config.SPLITS_DIR / f"{split}.csv").assign(split=split))
    pv_h = sorted((config.PLANTVILLAGE_DIR / "raw" / "color" / "Potato___healthy").glob("*.[jJ][pP]*[gG]"))
    if not pv_h:
        raise SystemExit("Missing PlantVillage Potato___healthy. Run: git -C datasets/plantvillage sparse-checkout add "
                         "'/raw/color/Potato___healthy/'")
    h = pd.DataFrame({"path": [p.relative_to(config.DATASETS_DIR).as_posix() for p in pv_h], "label": "potato_healthy",
                      "source": "plantvillage"})
    tr, rest = train_test_split(h, test_size=0.2, random_state=config.SEED)
    va, te = train_test_split(rest, test_size=0.5, random_state=config.SEED)
    frames += [tr.assign(split="lab_train"), va.assign(split="lab_val"), te.assign(split="lab_test")]

    # PlantDoc field photos: identical assignment to v1.
    for v1, v2 in (("final_field_train", "field_train"), ("final_field_val", "field_val"),
                   ("final_field_cal", "field_cal"), ("field_test", "field_test")):
        frames.append(pd.read_csv(config.SPLITS_DIR / f"{v1}.csv").assign(split=v2, source="plantdoc"))

    # Tanzania: random per-class split.
    tz = extract_tanzania(config.SEED)
    tz["md5"] = [md5(config.DATASETS_DIR / p) for p in tz["path"]]
    tz = tz.drop_duplicates("md5")
    for label, g in tz.groupby("label"):
        g = g.sample(frac=1, random_state=config.SEED)
        start = 0
        for split, n in TZ_COUNTS.items():
            frames.append(g.iloc[start:start + n].assign(split=f"field_{split}"))
            start += n

    # Tomato-Village: training only.
    tv_rows, unknown = [], []
    for p in sorted(TV_DIR.rglob("*.jp*g")):
        cls = p.parts[-2]
        rel = p.relative_to(config.DATASETS_DIR).as_posix()
        if cls in TV_CLASSES:
            tv_rows.append({"path": rel, "label": TV_CLASSES[cls], "source": "tomato_village", "split": "field_train"})
        elif cls in TV_UNKNOWN:
            unknown.append({"path": rel, "disease": cls, "crop": "tomato", "source": "tomato_village"})
    frames.append(pd.DataFrame(tv_rows))

    df = pd.concat(frames, ignore_index=True)
    df["md5"] = [m if isinstance(m, str) else md5(config.DATASETS_DIR / p) for p, m in zip(df["path"], df.get("md5"))]
    before = len(df)
    # Exact duplicates across ALL sources: keep the copy in the most "protected" split (test > cal > val > train).
    rank = {"field_test": 0, "lab_test": 0, "field_cal": 1, "field_val": 2, "lab_val": 2, "field_train": 3, "lab_train": 3}
    df = df.assign(_r=df["split"].map(rank)).sort_values(["md5", "_r"]).drop_duplicates("md5").drop(columns="_r")
    print(f"exact duplicates removed: {before - len(df)}")

    # Near-duplicate check for Tanzania test vs train (perceptual hash, <= 4 of 64 bits different).
    tz_test = df[(df["source"] == "tanzania") & (df["split"] == "field_test")]
    tz_train = df[(df["source"] == "tanzania") & (df["split"] == "field_train")]
    Htr = np.array([dhash(config.DATASETS_DIR / p) for p in tz_train["path"]])
    drop = [i for i, p in zip(tz_test.index, tz_test["path"])
            if ((Htr != dhash(config.DATASETS_DIR / p)).sum(1) <= 4).any()]
    df = df.drop(index=drop)
    print(f"Tanzania test photos with a near-twin in train (removed): {len(drop)}")

    df["label_idx"] = df["label"].map(label_idx)
    cols = ["path", "label", "label_idx", "source", "md5"]
    for split, part in df.groupby("split"):
        part.sort_values("path")[cols].to_csv(OUT / f"{split}.csv", index=False)
    pd.DataFrame(unknown).to_csv(OUT / "unknown_probe.csv", index=False)
    (OUT / "classes.json").write_text(json.dumps(V2_CLASSES, indent=2))
    table = df.pivot_table(index="label", columns=["split", "source"], values="path", aggfunc="count", fill_value=0)
    table.to_csv(config.OUTPUTS_DIR / "class_counts_v2.csv")
    print(df.pivot_table(index="label", columns="split", values="path", aggfunc="count", fill_value=0).to_string())
    print(f"unknown-disease probe: {len(unknown)} photos ({', '.join(TV_UNKNOWN)})")


if __name__ == "__main__":
    main()
