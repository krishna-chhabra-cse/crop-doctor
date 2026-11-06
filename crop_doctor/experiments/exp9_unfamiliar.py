"""Experiment 9: can the app notice a photo of a disease it was never taught?

    python -m crop_doctor.experiments.exp9_unfamiliar

Problem (Exp 8): on 2,909 Tomato-Village photos of diseases the model never learned (leaf miner, spotted wilt,
nutrient deficiencies), the assistant still named ONE of its 11 diseases 43% of the time. Conformal sets only
cover the 11 known classes, so they can't fix this.

Idea: an "unfamiliar photo" score from the model's raw outputs, the ENERGY score (Liu et al., NeurIPS 2020):
  energy = log(sum(exp(logits)))  over the farmer's crop.  High = the photo strongly activates some known class.
We also report the max-probability score as a baseline. Energy was chosen BEFORE looking at any results.

Threshold: from KNOWN field photos only (field_val), per crop: the 5th percentile, so ~5% of genuine photos are
flagged. No unknown photo is used to choose it. Flagged photos go to an expert instead of getting an answer.

Evaluation:
- unknown probe (2,909 tomato photos): how many are flagged, and how often one disease is still named;
- known field test (1,306 photos): how many are flagged (the cost), and accuracy of the answers that remain;
- confound check: Tomato-Village photos are taken on paper, so a detector could just flag "paper". We score the
  KNOWN Tomato-Village photos too (same camera setup). They were in training, so this check is optimistic.

Scores use the exact ONNX model the server runs, so the threshold is valid on the server.

RESULT (6 Nov 2026): it does NOT work here. AUROC 0.18 (energy) / 0.39 (max-prob): the model is MORE confident on
the unknown Tomato-Village photos than on real known field photos, because Tomato-Village's setup (leaves on
paper) was in training, so those photos look "familiar", while real farm photos are messy. 0% of unknown photos
flagged, 8% of known photos flagged. Output-confidence scores can't tell "new disease" from "familiar-looking
photo". So the gate is NOT shipped (see `shipped`). Next step: train an explicit "something else" class with
outlier exposure, and test it on held-out unknown diseases.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from PIL import Image
from scipy.special import logsumexp
from sklearn.metrics import roc_auc_score

from crop_doctor import config
from crop_doctor.model.backends import OnnxBackend
from crop_doctor.model.crops import crop_of, crops_from_labels, mask_logits
from crop_doctor.uncertainty.calibration import softmax
from crop_doctor.uncertainty.conformal import group_prediction_sets, uniform_noise

ASSETS = config.ROOT / "server" / "assets"
SPLITS = config.ROOT / "crop_doctor" / "data" / "splits_v2"
CACHE = config.OUTPUTS_DIR / "cache_exp9"
TARGET_FLAG_RATE = 0.05


def energy(logits: np.ndarray) -> np.ndarray:
    return logsumexp(logits, axis=1)            # -inf entries (other crop) contribute 0


def max_prob(logits: np.ndarray, t: float) -> np.ndarray:
    return softmax(logits, t).max(1)


def onnx_logits(backend, paths: list[str], name: str, crop: str | list[str], classes: list[str]) -> np.ndarray:
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / f"{name}.npy"
    if f.exists():
        return np.load(f)
    raw = []
    for i, p in enumerate(paths):
        with Image.open(config.DATASETS_DIR / p) as im:
            raw.append(backend.raw_logits(im))
        if i % 500 == 0:
            print(f"    {name}: {i}/{len(paths)}", flush=True)
    crops = [crop] * len(paths) if isinstance(crop, str) else crop
    out = mask_logits(np.array(raw), classes, crops)
    np.save(f, out)
    return out


def main() -> None:
    app = json.loads((ASSETS / "app_model.json").read_text())
    classes, t = app["classes"], app["temperature"]
    qhat = app["qhat"]["0.1"]
    model = ASSETS / "model_fp32.onnx"
    backend = OnnxBackend(model if model.exists() else ASSETS / app["onnx"], classes)

    def cached(split):                          # known photos: logits already computed by export_onnx
        d = np.load(ASSETS / "logits" / f"{split}.npz")
        return d["logits"], d["labels"]

    val_l, val_y = cached("field_val")
    test_l, test_y = cached("field_test")
    probe = pd.read_csv(SPLITS / "unknown_probe.csv")
    probe_l = onnx_logits(backend, probe["path"].tolist(), "unknown_probe", "tomato", classes)
    tv = pd.read_csv(SPLITS / "field_train.csv").query("source == 'tomato_village'")
    tv_l = onnx_logits(backend, tv["path"].tolist(), "tomato_village_known", "tomato", classes)

    val_crops = crops_from_labels(val_y, classes)
    test_crops = crops_from_labels(test_y, classes)
    res = {"target_flag_rate_on_known": TARGET_FLAG_RATE, "scores": {}}
    for name, score in [("energy", energy), ("max_prob", lambda l: max_prob(l, t))]:
        thr = {c: float(np.quantile(score(val_l[val_crops == c]), TARGET_FLAG_RATE)) for c in ("potato", "tomato")}
        flag_test = score(test_l) < np.array([thr[c] for c in test_crops])
        flag_probe = score(probe_l) < thr["tomato"]
        flag_tv = score(tv_l) < thr["tomato"]
        tom = test_crops == "tomato"
        auroc = roc_auc_score(np.r_[np.ones(tom.sum()), np.zeros(len(probe_l))],
                              np.r_[score(test_l[tom]), score(probe_l)])
        res["scores"][name] = {"threshold": thr, "auroc_tomato_known_vs_unknown": float(auroc),
                               "unknown_flagged": float(flag_probe.mean()),
                               "known_test_flagged": float(flag_test.mean()),
                               "known_tomato_village_flagged": float(flag_tv.mean())}

    # Effect on the assistant (energy gate): "names one disease" = shortlist of one.
    thr = res["scores"]["energy"]["threshold"]
    sets_p = group_prediction_sets(softmax(probe_l, t), qhat, np.array(["tomato"] * len(probe_l)),
                                   uniform_noise(len(probe_l), 12345))
    size_p = sets_p.sum(1)
    gate_p = energy(probe_l) < thr["tomato"]
    sets_k = group_prediction_sets(softmax(test_l, t), qhat, test_crops, uniform_noise(len(test_l), 12345))
    size_k = sets_k.sum(1)
    gate_k = energy(test_l) < np.array([thr[c] for c in test_crops])
    right_k = (size_k == 1) & sets_k[np.arange(len(test_y)), test_y]
    one_k = size_k == 1
    res["assistant"] = {
        "unknown_named_one_disease_before": float((size_p == 1).mean()),
        "unknown_named_one_disease_after": float(((size_p == 1) & ~gate_p).mean()),
        "known_answered_before": float(one_k.mean()),
        "known_answered_after": float((one_k & ~gate_k).mean()),
        "known_accuracy_when_answered_before": float(right_k[one_k].mean()),
        "known_accuracy_when_answered_after": float(right_k[one_k & ~gate_k].mean()),
        "known_correct_answers_sent_to_expert": float((right_k & gate_k).sum() / max(right_k.sum(), 1)),
    }
    out = config.OUTPUTS_DIR / "metrics" / "exp9_unfamiliar.json"
    out.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))

    # Ship the gate ONLY if it actually helps: it must cut "names one disease on an unknown photo" by at least
    # 10 points. Otherwise it would only send correct answers to experts, so the server keeps it switched off.
    a = res["assistant"]
    helps = a["unknown_named_one_disease_before"] - a["unknown_named_one_disease_after"] >= 0.10
    res["shipped"] = bool(helps)
    if helps:
        app["unfamiliar"] = {"score": "energy", "threshold": thr, "flag_rate_on_known_val": TARGET_FLAG_RATE}
    else:
        app.pop("unfamiliar", None)
    (ASSETS / "app_model.json").write_text(json.dumps(app, indent=2))
    out.write_text(json.dumps(res, indent=2))
    print("gate shipped" if helps else "gate NOT shipped: it doesn't catch unknown diseases on this data")


if __name__ == "__main__":
    main()
