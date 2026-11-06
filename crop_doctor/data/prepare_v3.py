"""Build the v3 splits: v2 + a 12th class, "something else" (outlier exposure), for TOMATO only.

    python -m crop_doctor.data.prepare_v3

v2 (crop_doctor/data/splits_v2/) is NOT changed. v3 writes crop_doctor/data/splits_v3/.

The unknown Tomato-Village problems are split BY DISEASE, never by photo:
  taught as "something else"   Leaf Miner, Magnesium Deficiency       -> other_train / other_val
  held out, never seen         Spotted Wilt Virus, Nitrogen Deficiency, Potassium Deficiency -> unknown_heldout
So the test asks the real question: does "something else" fire on a problem the model has NEVER seen?

Confound control: Tomato-Village photos are leaves on paper. If "something else" just learned "paper photo that
isn't early/late blight/healthy", it would also fire on KNOWN Tomato-Village photos it never trained on. So ~10% of
the known Tomato-Village training photos are held out (tv_known_holdout) and never trained on, as a check.

Leak checks: Tomato-Village contains rotated near-copies. Photos are grouped by a rotation-aware perceptual hash
(<= 4 of 64 bits different under any 90-degree rotation) and every group stays on one side of each split; exact
copies (MD5) of a held-out photo are removed from training.

Class order: v2's 11 classes, then "tomato_something_else" appended LAST, so every v2 label_idx is unchanged.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
from PIL import Image

from crop_doctor import config

V2 = config.ROOT / "crop_doctor" / "data" / "splits_v2"
OUT = config.ROOT / "crop_doctor" / "data" / "splits_v3"
OTHER = "tomato_something_else"
TAUGHT = ["Leaf Miner", "Magnesium Deficiency"]
HELD_OUT = ["Spotted Wilt Virus", "Nitrogen Deficiency", "Pottassium Deficiency"]
OTHER_VAL_SHARE = 0.15
TV_KNOWN_HOLDOUT_SHARE = 0.10
NEAR = 4            # max differing bits (of 64) to count as a near-copy


def md5(path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def dhashes(path, n: int = 8) -> np.ndarray:
    """(4, 64) difference hashes of the photo at 0/90/180/270 degrees."""
    with Image.open(path) as im:
        g = im.convert("L")
        out = []
        for k in range(4):
            a = np.asarray(g.rotate(90 * k, expand=True).resize((n + 1, n)), dtype=np.int16)
            out.append((a[:, 1:] > a[:, :-1]).ravel())
    return np.array(out)


def near_groups(H: np.ndarray) -> np.ndarray:
    """Union-find over photos whose hashes are near-copies under any rotation. H: (n, 4, 64). Returns group ids."""
    n = len(H)
    parent = np.arange(n)

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    base = H[:, 0, :]
    for i in range(n):
        d = (H[i][:, None, :] != base[None, :, :]).sum(2).min(0)     # min over rotations of photo i
        for j in np.nonzero(d <= NEAR)[0]:
            if j != i:
                parent[find(i)] = find(j)
    return np.array([find(i) for i in range(n)])


def near_any(Hq: np.ndarray, Href: np.ndarray) -> np.ndarray:
    """For each query photo: does it have a near-copy (any rotation) among the reference photos?"""
    base = Href[:, 0, :]
    return np.array([((h[:, None, :] != base[None, :, :]).sum(2).min(0) <= NEAR).any() for h in Hq])


def group_split(df: pd.DataFrame, groups: np.ndarray, share: float, seed: int) -> np.ndarray:
    """Boolean mask of rows in the held-out part: whole near-copy groups, ~share of photos, stratified by `strat`."""
    rng = np.random.default_rng(seed)
    hold = np.zeros(len(df), bool)
    for _, idx in df.groupby("strat").indices.items():
        g = np.unique(groups[idx])
        rng.shuffle(g)
        target, got = share * len(idx), 0
        for gid in g:
            if got >= target:
                break
            m = groups == gid
            hold |= m
            got += m.sum()
    return hold


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    classes = json.loads((V2 / "classes.json").read_text()) + [OTHER]
    probe = pd.read_csv(V2 / "unknown_probe.csv")
    probe["md5"] = [md5(config.DATASETS_DIR / p) for p in probe["path"]]
    before = len(probe)
    probe = probe.drop_duplicates("md5")
    print(f"unknown photos: {before}, exact copies removed: {before - len(probe)}")
    print("hashing ...", flush=True)
    H = np.array([dhashes(config.DATASETS_DIR / p) for p in probe["path"]])

    taught = probe["disease"].isin(TAUGHT).to_numpy()
    held = probe["disease"].isin(HELD_OUT).to_numpy()
    # A held-out photo with a near-copy among the taught photos would leak: drop it from the held-out test.
    leak = np.zeros(len(probe), bool)
    leak[held] = near_any(H[held], H[taught])
    print(f"held-out photos with a near-copy among taught photos (dropped from test): {leak.sum()}")
    heldout = probe[held & ~leak][["path", "disease", "crop", "source", "md5"]]

    tdf = probe[taught].assign(strat=lambda d: d["disease"]).reset_index(drop=True)
    tg = near_groups(H[taught])
    is_val = group_split(tdf, tg, OTHER_VAL_SHARE, config.SEED)
    tdf = tdf.assign(label=OTHER, label_idx=classes.index(OTHER))
    cols = ["path", "label", "label_idx", "source", "md5"]

    # Known Tomato-Village photos: hold ~10% out of training (whole near-copy groups) for the paper-confound check.
    ftr = pd.read_csv(V2 / "field_train.csv")
    tv = ftr[ftr["source"] == "tomato_village"].assign(strat=lambda d: d["label"])
    Htv = np.array([dhashes(config.DATASETS_DIR / p) for p in tv["path"]])
    tv_hold = group_split(tv.reset_index(drop=True), near_groups(Htv), TV_KNOWN_HOLDOUT_SHARE, config.SEED + 1)
    hold_idx = tv.index[tv_hold]
    field_train = ftr.drop(index=hold_idx)

    other_train = tdf[~is_val].copy()
    other_val = tdf[is_val].copy()
    # The taught training photos must not be near-copies of any held-out check photo either.
    Hhold = Htv[tv_hold]
    clash = near_any(H[taught][~is_val], np.concatenate([Hhold, H[held & ~leak]]))
    other_train = other_train[~clash]
    print(f"taught training photos dropped as near-copies of a held-out check photo: {clash.sum()}")

    for name in ("lab_train", "lab_val", "lab_test", "field_val", "field_cal", "field_test"):
        pd.read_csv(V2 / f"{name}.csv").to_csv(OUT / f"{name}.csv", index=False)
    field_train.to_csv(OUT / "field_train.csv", index=False)
    other_train.sort_values("path")[cols + ["disease"]].to_csv(OUT / "other_train.csv", index=False)
    other_val.sort_values("path")[cols + ["disease"]].to_csv(OUT / "other_val.csv", index=False)
    ftr.loc[hold_idx].sort_values("path").to_csv(OUT / "tv_known_holdout.csv", index=False)
    heldout.sort_values("path").to_csv(OUT / "unknown_heldout.csv", index=False)
    (OUT / "classes.json").write_text(json.dumps(classes, indent=2))
    print(f"other_train {len(other_train)} {other_train['disease'].value_counts().to_dict()}")
    print(f"other_val   {len(other_val)} {other_val['disease'].value_counts().to_dict()}")
    print(f"tv_known_holdout {len(hold_idx)} {ftr.loc[hold_idx, 'label'].value_counts().to_dict()}; "
          f"field_train {len(ftr)} -> {len(field_train)}")
    print(f"unknown_heldout {len(heldout)} {heldout['disease'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
