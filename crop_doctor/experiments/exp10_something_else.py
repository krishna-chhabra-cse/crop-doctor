"""Experiment 10: teach the model an explicit "something else" class (outlier exposure) and test it on diseases
it has NEVER seen.

    python -m crop_doctor.data.prepare_v3                                                     # splits_v3
    python -m crop_doctor.model.train_v2 --splits splits_v3 --tag final_v3_convnext_tiny     # ~25 min
    python -m crop_doctor.experiments.exp10_something_else

Background (Exp 8/9): on never-taught tomato problems, v2 still names exactly one of its 11 diseases ~44% of the
time, and confidence scores (energy, max-prob) can't flag them (Exp 9, AUROC 0.18).

Idea (Hendrycks et al. 2019, "outlier exposure"): give the model a 12th class, "something else", trained on
photos of OTHER tomato problems. Split BY DISEASE (crop_doctor/data/prepare_v3.py):
  taught as "something else": Leaf Miner, Magnesium Deficiency
  held out, never seen:       Spotted Wilt Virus, Nitrogen Deficiency, Potassium Deficiency (unknown_heldout)

Rules fixed BEFORE looking at results:
- Temperature and per-crop (Mondrian) conformal thresholds are fitted on field_cal (KNOWN photos only), exactly
  as for v2, so the 90% promise still refers to the 11 known diseases.
- The assistant sends a photo to an expert when "something else" is the model's TOP answer (primary rule).
  We also report the stricter rule "something else is anywhere in the shortlist".
- "Names one known disease" = the shortlist is exactly one known disease and the photo isn't routed away.
- Ship only if, on unknown_heldout, "names one known disease" drops by >= 10 points vs v2 on the SAME photos,
  AND on the known field test (1,306 photos) accuracy drops by <= 1 point and coverage stays >= 88.5%.

Confound (be honest): every "something else" training photo AND every held-out unknown photo is a Tomato-Village
leaf on paper. The class could learn "paper photo that isn't early blight / late blight / healthy". Checks:
- tv_known_holdout: 166 KNOWN Tomato-Village photos (early/late blight, healthy) that v3 never trained on.
  If "something else" fires a lot there, it learned the background, not the disease.
- PlantDoc tomato test photos (real backgrounds): how often "something else" fires on known diseases.
What we can NOT test: unknown diseases photographed in a real field (we have none).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from crop_doctor import config
from crop_doctor.experiments.common import save_metrics
from crop_doctor.experiments.exp8_final_v2 import raw_logits
from crop_doctor.model.common import device
from crop_doctor.model.crops import crops_from_labels, mask_logits
from crop_doctor.uncertainty.calibration import fit_temperature, softmax
from crop_doctor.uncertainty.conformal import evaluate_sets, group_prediction_sets, group_quantiles, uniform_noise

V3 = config.ROOT / "crop_doctor" / "data" / "splits_v3"
CACHE = config.OUTPUTS_DIR / "cache_exp10"
OTHER = "tomato_something_else"
MODELS = {"v2": "final_v2_convnext_tiny.pt", "v3": "final_v3_convnext_tiny.pt"}
ALPHA = 0.1
MIN_DROP, MAX_ACC_DROP, MIN_COVERAGE = 0.10, 0.01, 0.885


def logits_for(tag: str, name: str, df: pd.DataFrame, classes: list[str], crops, dev) -> np.ndarray:
    """Crop-masked logits in v3's 12-column order (v2 has no "something else": that column is -inf)."""
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{tag}_{name}.npy"
    if f.exists():
        return np.load(f)
    lg, model_classes = raw_logits(MODELS[tag], df, dev)
    out = np.full((len(df), len(classes)), -np.inf)
    for j, c in enumerate(model_classes):
        out[:, classes.index(c)] = lg[:, j]
    out = mask_logits(out, classes, crops)
    np.save(f, out)
    return out


def behaviour(probs: np.ndarray, sets: np.ndarray, other: int | None) -> dict[str, np.ndarray]:
    """What the assistant does with each photo (before any follow-up question is answered)."""
    size = sets.sum(1)
    top_other = probs.argmax(1) == other if other is not None else np.zeros(len(probs), bool)
    in_set_other = sets[:, other] if other is not None else np.zeros(len(probs), bool)
    named = (size == 1) & ~in_set_other & ~top_other
    return {"named_one_known": named, "something_else_top": top_other,
            "question": ~top_other & (size >= 2) & (size <= 3),
            "expert": top_other | (size == 0) | (size > 3),
            "something_else_in_shortlist": in_set_other}


def rates(b: dict[str, np.ndarray], mask: np.ndarray | None = None) -> dict[str, float]:
    mask = np.ones(len(next(iter(b.values()))), bool) if mask is None else mask
    return {k: round(float(v[mask].mean()), 4) for k, v in b.items()}


def main() -> None:
    dev = device()
    classes = json.loads((V3 / "classes.json").read_text())
    other = classes.index(OTHER)
    known = {s: pd.read_csv(V3 / f"{s}.csv") for s in ("field_cal", "field_test", "tv_known_holdout", "other_val")}
    unk = pd.read_csv(V3 / "unknown_heldout.csv")

    res = {"rules": {"route_to_expert": "'something else' is the top answer", "alpha": ALPHA,
                     "ship_if": {"unknown_named_one_known_drop_at_least": MIN_DROP,
                                 "field_test_accuracy_drop_at_most": MAX_ACC_DROP,
                                 "field_test_coverage_at_least": MIN_COVERAGE}},
           "photos": {**{k: len(v) for k, v in known.items()}, "unknown_heldout": len(unk)}}
    for tag in MODELS:
        L = {s: logits_for(tag, s, d, classes, crops_from_labels(d["label_idx"].to_numpy(), classes), dev)
             for s, d in known.items()}
        L["unknown_heldout"] = logits_for(tag, "unknown_heldout", unk, classes, ["tomato"] * len(unk), dev)
        cal_y = known["field_cal"]["label_idx"].to_numpy()
        t = fit_temperature(L["field_cal"], cal_y)
        qhat = group_quantiles(softmax(L["field_cal"], t), cal_y, crops_from_labels(cal_y, classes), ALPHA,
                               uniform_noise(len(cal_y), 7))
        o = other if tag == "v3" else None
        r = {"temperature": t, "qhat": qhat}

        def run(name, crops, seed):
            p = softmax(L[name], t)
            s = group_prediction_sets(p, qhat, np.asarray(crops), uniform_noise(len(p), seed))
            return p, s

        # Known field test (1,306 photos).
        te = known["field_test"]
        y = te["label_idx"].to_numpy()
        p, s = run("field_test", crops_from_labels(y, classes), 12345)
        b = behaviour(p, s, o)
        right = (p.argmax(1) == y)
        r["field_test"] = {"accuracy": round(float(right.mean()), 4), **evaluate_sets(s, y),
                           "assistant": rates(b),
                           "by_source": {}}
        for src in sorted(te["source"].unique()):
            m = (te["source"] == src).to_numpy()
            r["field_test"]["by_source"][src] = {"photos": int(m.sum()), "accuracy": round(float(right[m].mean()), 4),
                                                 **evaluate_sets(s[m], y[m]), "assistant": rates(b, m)}
        tom = (te["source"] == "plantdoc").to_numpy() & (crops_from_labels(y, classes) == "tomato")
        r["field_test"]["plantdoc_tomato_something_else_top"] = round(float(b["something_else_top"][tom].mean()), 4)

        # Held-out unknown problems (never seen by either model).
        p, s = run("unknown_heldout", ["tomato"] * len(unk), 99)
        b = behaviour(p, s, o)
        r["unknown_heldout"] = {"all": rates(b), "by_disease": {
            d: rates(b, (unk["disease"] == d).to_numpy()) for d in sorted(unk["disease"].unique())}}

        # Taught "something else" diseases, unseen photos (did it learn the class at all?).
        ov = known["other_val"]
        p, s = run("other_val", ["tomato"] * len(ov), 5)
        r["other_val_taught_diseases_new_photos"] = rates(behaviour(p, s, o))

        # Confound check: known Tomato-Village photos v3 never trained on (v2 DID train on them: optimistic).
        tv = known["tv_known_holdout"]
        ty = tv["label_idx"].to_numpy()
        p, s = run("tv_known_holdout", ["tomato"] * len(tv), 3)
        r["tv_known_holdout"] = {"accuracy": round(float((p.argmax(1) == ty).mean()), 4), **evaluate_sets(s, ty),
                                 "assistant": rates(behaviour(p, s, o)),
                                 "note": "v2 trained on these photos" if tag == "v2" else "never trained on"}
        res[tag] = r
        print(f"{tag}: field_test acc {r['field_test']['accuracy']:.3f} cov {r['field_test']['coverage']:.3f} "
              f"set {r['field_test']['avg_set_size']:.2f} | unknown named-one {r['unknown_heldout']['all']['named_one_known']:.3f} "
              f"SE {r['unknown_heldout']['all']['something_else_top']:.3f} expert {r['unknown_heldout']['all']['expert']:.3f} | "
              f"TV-known SE {r['tv_known_holdout']['assistant']['something_else_top']:.3f} acc {r['tv_known_holdout']['accuracy']:.3f}",
              flush=True)

    v2, v3 = res["v2"], res["v3"]
    drop = v2["unknown_heldout"]["all"]["named_one_known"] - v3["unknown_heldout"]["all"]["named_one_known"]
    acc_drop = v2["field_test"]["accuracy"] - v3["field_test"]["accuracy"]
    cov = v3["field_test"]["coverage"]
    res["decision"] = {"unknown_named_one_known_drop": round(drop, 4), "field_test_accuracy_drop": round(acc_drop, 4),
                       "v3_field_test_coverage": cov,
                       "ship": bool(drop >= MIN_DROP and acc_drop <= MAX_ACC_DROP and cov >= MIN_COVERAGE)}
    save_metrics("exp10_something_else", res)
    print(json.dumps(res["decision"], indent=2))


if __name__ == "__main__":
    main()
