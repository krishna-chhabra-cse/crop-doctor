"""Near-duplicate audit: does any test (or calibration) photo have a resized / re-saved / rotated twin in another split?

    python -m crop_doctor.data.near_duplicates
    python -m crop_doctor.data.near_duplicates --datasets "C:/path/to/datasets"   # if the photos live elsewhere

Why: prepare.py / prepare_v2.py removed EXACT copies (same MD5 = same bytes). A photo that was resized or saved again
has different bytes, so MD5 misses it. PlantDoc is collected from the web, where the same picture often appears in
several sizes; Tanzania has burst shots of the same leaf. This script looks for those "twins" in the v3 splits.

How:
1. Every photo gets a difference hash (dHash, 64 bits) at 0/90/180/270 degrees (the same hash as prepare_v3.py).
   Two photos are CANDIDATE twins if at most 4 of the 64 bits differ under some rotation.
2. A hash match can be a coincidence (two different, plain-looking photos), so each candidate is CONFIRMED only if
   their small grey thumbnails (32x32) are almost identical: pixel correlation > 0.9 under the best rotation.
3. Sensitivity: accuracy and 90% shortlist coverage on field_test, with and without the test photos that have a
   confirmed twin in a training / validation / calibration split. Uses the cached model outputs from Exp 10
   (outputs/cache_exp10) and the same temperature + per-crop thresholds as the app (fitted on field_cal).
   Also refits the thresholds without the calibration photos that have a twin in training.

Writes outputs/metrics/near_duplicates.json (numbers and file paths only; no images). Splits are NOT changed.
"""
from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from crop_doctor import config
from crop_doctor.data.prepare_v3 import NEAR, dhashes
from crop_doctor.model.crops import crops_from_labels
from crop_doctor.uncertainty.calibration import fit_temperature, softmax
from crop_doctor.uncertainty.conformal import evaluate_sets, group_prediction_sets, group_quantiles, uniform_noise

SPLITS = config.ROOT / "crop_doctor" / "data" / "splits_v3"
CACHE = config.OUTPUTS_DIR / "cache_exp10"
OUT = config.OUTPUTS_DIR / "metrics" / "near_duplicates.json"
FIELD_SPLITS = ("field_train", "field_val", "field_cal", "field_test")
MIN_CORR = 0.9          # thumbnails this similar = the same photo
ALPHA = 0.1


# ---------- finding twins ----------

def thumbnail(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("L").resize((32, 32)), dtype=np.float64)


def best_corr(a: np.ndarray, b: np.ndarray) -> float:
    """Pixel correlation of two thumbnails under the best of 4 rotations of `a` (1 = identical)."""
    out = []
    for k in range(4):
        x, y = np.rot90(a, k).ravel(), b.ravel()
        out.append(0.0 if x.std() == 0 or y.std() == 0 else float(np.corrcoef(x, y)[0, 1]))
    return max(out)


def candidate_pairs(Hq: np.ndarray, Hr: np.ndarray, near: int = NEAR) -> list[tuple[int, int, int]]:
    """(query row, reference row, differing bits) for every query/reference pair within `near` bits under some
    rotation of the query. Hq: (nq, 4, 64), Hr: (nr, 4, 64)."""
    base = Hr[:, 0, :]
    out = []
    for i, h in enumerate(Hq):
        d = (h[:, None, :] != base[None, :, :]).sum(2).min(0)
        out += [(i, int(j), int(d[j])) for j in np.nonzero(d <= near)[0]]
    return out


def confirmed_pairs(paths_q: list[Path], Hq, paths_r: list[Path], Hr, min_corr: float = MIN_CORR) -> list[dict]:
    out = []
    for i, j, d in candidate_pairs(Hq, Hr):
        c = best_corr(thumbnail(paths_q[i]), thumbnail(paths_r[j]))
        out.append({"q": i, "r": j, "bits": d, "corr": round(c, 3), "confirmed": c > min_corr})
    return out


# ---------- sensitivity ----------

def calibrate(cal_logits, cal_y, classes):
    t = fit_temperature(cal_logits, cal_y)
    q = group_quantiles(softmax(cal_logits, t), cal_y, crops_from_labels(cal_y, classes), ALPHA,
                        uniform_noise(len(cal_y), 7))
    return t, q


def scores(test_logits, y, classes, t, q, mask) -> dict:
    p = softmax(test_logits, t)
    sets = group_prediction_sets(p, q, crops_from_labels(y, classes), uniform_noise(len(y), 12345))
    e = evaluate_sets(sets[mask], y[mask])
    return {"photos": int(mask.sum()), "accuracy": round(float((p.argmax(1) == y)[mask].mean()), 4),
            "coverage": round(e["coverage"], 4), "avg_set_size": round(e["avg_set_size"], 3)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", type=Path, default=config.DATASETS_DIR, help="folder that holds the photos")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    classes = json.loads((SPLITS / "classes.json").read_text())
    df = {s: pd.read_csv(SPLITS / f"{s}.csv") for s in FIELD_SPLITS}
    paths = {s: [args.datasets / p for p in d["path"]] for s, d in df.items()}
    print("hashing photos ...", flush=True)
    with ThreadPoolExecutor(args.workers) as ex:
        H = {s: np.array(list(ex.map(dhashes, paths[s]))) for s in FIELD_SPLITS}

    def compare(qs, rs, q_src=None, r_src=None):
        qm = np.ones(len(df[qs]), bool) if q_src is None else (df[qs]["source"] == q_src).to_numpy()
        rm = np.ones(len(df[rs]), bool) if r_src is None else (df[rs]["source"] == r_src).to_numpy()
        qi, ri = np.nonzero(qm)[0], np.nonzero(rm)[0]
        pairs = confirmed_pairs([paths[qs][i] for i in qi], H[qs][qi], [paths[rs][j] for j in ri], H[rs][ri])
        for p in pairs:
            p["q"], p["r"] = int(qi[p["q"]]), int(ri[p["r"]])
            p["same_label"] = bool(df[qs]["label"].iat[p["q"]] == df[rs]["label"].iat[p["r"]])
        conf = [p for p in pairs if p["confirmed"]]
        summary = {"query_photos": int(qm.sum()), "reference_photos": int(rm.sum()),
                   "candidate_pairs": len(pairs), "confirmed_pairs": len(conf),
                   "query_photos_with_confirmed_twin": len({p["q"] for p in conf}),
                   "confirmed_pairs_with_different_label": sum(not p["same_label"] for p in conf)}
        return summary, conf

    res = {"method": {"hash": "dHash 64 bits, 4 rotations", "max_differing_bits": NEAR,
                      "confirm": f"32x32 grey thumbnail correlation > {MIN_CORR} (best rotation)"},
           "comparisons": {}, "plantdoc_test_twins": []}
    twin_test = np.zeros(len(df["field_test"]), bool)        # test photo with a twin in train / val / cal
    twin_cal = np.zeros(len(df["field_cal"]), bool)          # calibration photo with a twin in train
    checks = [("field_test", r, s, s) for s in ("plantdoc", "tanzania") for r in ("field_train", "field_val", "field_cal")]
    checks += [("field_test", "field_train", "plantdoc", "tomato_village")]
    checks += [(q, r, "tanzania", "tanzania") for q, r in (("field_cal", "field_train"), ("field_val", "field_train"),
                                                          ("field_cal", "field_val"))]
    checks += [(q, r, "plantdoc", "plantdoc") for q, r in (("field_cal", "field_train"), ("field_val", "field_train"),
                                                          ("field_cal", "field_val"))]
    for qs, rs, q_src, r_src in checks:
        summary, conf = compare(qs, rs, q_src, r_src)
        key = f"{qs}[{q_src}] vs {rs}[{r_src}]"
        res["comparisons"][key] = summary
        print(f"  {key:<52} twins {summary['query_photos_with_confirmed_twin']:>3} "
              f"(candidates {summary['candidate_pairs']}, different label {summary['confirmed_pairs_with_different_label']})")
        for p in conf:
            if qs == "field_test":
                twin_test[p["q"]] = True
            if qs == "field_cal" and rs == "field_train":
                twin_cal[p["q"]] = True
            if qs == "field_test" and q_src == "plantdoc":
                res["plantdoc_test_twins"].append({
                    "test": df[qs]["path"].iat[p["q"]], "test_label": df[qs]["label"].iat[p["q"]],
                    "twin": df[rs]["path"].iat[p["r"]], "twin_label": df[rs]["label"].iat[p["r"]],
                    "twin_split": rs, "bits": p["bits"], "corr": p["corr"]})

    src = df["field_test"]["source"].to_numpy()
    pd_twins = res["plantdoc_test_twins"]
    res["summary"] = {
        "plantdoc_test_photos_with_twin": int(twin_test[src == "plantdoc"].sum()),
        "plantdoc_test_photos_with_twin_different_label": len({t["test"] for t in pd_twins if t["test_label"] != t["twin_label"]}),
        "tanzania_test_photos_with_twin": int(twin_test[src == "tanzania"].sum()),
        "calibration_photos_with_twin_in_train": {s: int(twin_cal[(df["field_cal"]["source"] == s).to_numpy()].sum())
                                                   for s in ("plantdoc", "tanzania")},
    }

    # Sensitivity: does removing the twins change the reported results?
    y = df["field_test"]["label_idx"].to_numpy()
    cal_y = df["field_cal"]["label_idx"].to_numpy()
    res["sensitivity"] = {}
    for tag in ("v2", "v3"):
        lt, lc = np.load(CACHE / f"{tag}_field_test.npy"), np.load(CACHE / f"{tag}_field_cal.npy")
        t, q = calibrate(lc, cal_y, classes)                       # = the app's settings (exp10)
        t2, q2 = calibrate(lc[~twin_cal], cal_y[~twin_cal], classes)   # calibration without train twins
        r = {}
        for name, m in (("all", np.ones(len(y), bool)), ("plantdoc", src == "plantdoc"), ("tanzania", src == "tanzania")):
            r[name] = {"with_twins": scores(lt, y, classes, t, q, m),
                       "without_twins": scores(lt, y, classes, t, q, m & ~twin_test),
                       "without_twins_and_recalibrated": scores(lt, y, classes, t2, q2, m & ~twin_test)}
        res["sensitivity"][tag] = r
        a = r["all"]
        print(f"  {tag}: accuracy {a['with_twins']['accuracy']:.4f} -> {a['without_twins']['accuracy']:.4f}, "
              f"coverage {a['with_twins']['coverage']:.4f} -> {a['without_twins']['coverage']:.4f} "
              f"(recalibrated {a['without_twins_and_recalibrated']['coverage']:.4f}); PlantDoc accuracy "
              f"{r['plantdoc']['with_twins']['accuracy']:.4f} -> {r['plantdoc']['without_twins']['accuracy']:.4f}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(res, indent=2))
    print(json.dumps(res["summary"], indent=2))
    print(f"saved {OUT}")


if __name__ == "__main__":
    main()
