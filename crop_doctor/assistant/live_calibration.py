"""Real-time learning, the safe version: every expert label updates the app's confidence settings at once.

What changes instantly: the temperature T and the conformal threshold q-hat, recomputed from the current
"calibration points" (labelled photos + the model's outputs on them). The neural network itself does NOT change
here: retraining it is a separate, periodic step on expert-verified labels only (see train_final.py).

Rules (each one comes from our experiments):
- Lab photos are only a starting point. As soon as ANY field labels exist, calibrate on field labels only:
  lab and field photos are not exchangeable, so mixing them breaks the guarantee (Day 4: 32% coverage).
- Only RANDOM AUDIT photos (and the original field calibration set) may join the calibration set. Photos the
  assistant sent to experts are the hard ones, a biased sample; they go to the retraining pool instead.
- With fewer than 9 field photos, no finite 90% threshold exists: q-hat = inf, every disease stays possible,
  and everything goes to experts. That's the honest answer to "we don't know enough yet".

The trust meter: after every recalibration we measure coverage / shortlist size / answered-alone rate on a fixed
MONITOR set (field_test). It is only displayed, never used to fit anything.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from crop_doctor import config
from crop_doctor.app import db
from crop_doctor.model.crops import crops_from_labels, mask_logits
from crop_doctor.uncertainty.calibration import fit_temperature, softmax
from crop_doctor.uncertainty.conformal import (
    aps_scores, conformal_quantile, evaluate_sets, prediction_sets, uniform_noise,
)

ALPHA = 0.1
LAB = "lab_val"
FIELD_SOURCES = ("field_cal", "expert_audit", "simulated_expert")
SPLIT_FOR_SOURCE = {"lab_val": "lab_val", "field_cal": "final_field_cal", "simulated_expert": "final_field_val"}
MONITOR_SPLIT = "field_test"
CACHE = config.OUTPUTS_DIR / "live_logits"


def split_logits(split: str, doctor) -> tuple[np.ndarray, np.ndarray]:
    """Crop-masked logits of the app's model on a split (computed once, then cached on disk)."""
    path = CACHE / f"{split}.npz"
    if path.exists():
        d = np.load(path)
        return d["logits"], d["labels"]
    from torch.utils.data import DataLoader

    from crop_doctor.model.common import FrameDataset, eval_transform
    from crop_doctor.model.train_final import logits_of
    df = pd.read_csv(config.SPLITS_DIR / f"{split}.csv")
    y = df["label_idx"].to_numpy()
    dl = DataLoader(FrameDataset(df, eval_transform()), batch_size=64, num_workers=0)
    logits = mask_logits(logits_of(doctor.model, dl, doctor.dev), doctor.classes, crops_from_labels(y, doctor.classes))
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, logits=logits, labels=y)
    return logits, y


def calibration_set(points: list[dict]) -> tuple[np.ndarray, np.ndarray, int]:
    field = [p for p in points if p["source"] in FIELD_SOURCES]
    use = field if field else [p for p in points if p["source"] == LAB]
    if not use:
        return np.zeros((0, 0)), np.zeros(0, dtype=int), 0
    return np.array([p["logits"] for p in use]), np.array([p["label_idx"] for p in use]), len(field)


def fit(logits: np.ndarray, labels: np.ndarray) -> tuple[float, float]:
    if len(labels) == 0:
        return 1.0, float("inf")
    t = fit_temperature(logits, labels)
    qhat = conformal_quantile(aps_scores(softmax(logits, t), labels, uniform_noise(len(labels), 7)), ALPHA)
    return t, qhat


def recalibrate(doctor, note: str = "") -> dict:
    """Recompute T and q-hat from the stored points, apply them to the app, measure on the monitor set."""
    points = db.calibration_points()
    logits, labels, n_field = calibration_set(points)
    t, qhat = fit(logits, labels)
    doctor.set_calibration(t, qhat)
    mon_logits, mon_y = split_logits(MONITOR_SPLIT, doctor)
    sets = prediction_sets(softmax(mon_logits, t), qhat, uniform_noise(len(mon_y), 12345))
    m = evaluate_sets(sets, mon_y)
    run = {"n_points": len(labels), "n_field_points": n_field, "temperature": t, "qhat": qhat,
           "monitor_coverage": m["coverage"], "monitor_set_size": m["avg_set_size"],
           "monitor_answered": m["answered_rate"], "note": note}
    db.add_calibration_run(run)
    return run


def reset(doctor, base: str) -> dict:
    """base='field' (normal: start from the 95 field calibration photos) or 'lab' (demo: lab photos only)."""
    db.clear_calibration_points()
    source = "field_cal" if base == "field" else "lab_val"
    logits, y = split_logits(SPLIT_FOR_SOURCE[source], doctor)
    db.add_calibration_points([(source, None, int(yy), list(lg)) for lg, yy in zip(logits, y)])
    return recalibrate(doctor, note=f"reset to {base} calibration")


def ensure_initialised(doctor) -> dict:
    """First start: no points yet -> field calibration. Otherwise reapply the latest settings."""
    runs = db.calibration_runs()
    if not db.calibration_points():
        return reset(doctor, "field")
    last = runs[-1] if runs else recalibrate(doctor, note="startup")
    doctor.set_calibration(last["temperature"], last["qhat"])
    return last


def add_expert_label(doctor, case: dict, label: str) -> dict | None:
    """Expert labelled a RANDOM AUDIT case -> becomes a calibration point -> recalibrate now."""
    if not case.get("audit") or label not in doctor.classes:
        return None
    from PIL import Image
    probs_logits = doctor.logits(Image.open(db.IMAGES / case["image_path"]), case["crop"])
    db.add_calibration_points([("expert_audit", case["id"], doctor.classes.index(label), list(probs_logits))])
    return recalibrate(doctor, note=f"expert audit label (case {case['id']})")


def simulate_expert_labels(doctor, k: int, seed: int) -> dict:
    """Demo: k random photos from final_field_val (not used for training or calibration) arrive with labels."""
    logits, y = split_logits(SPLIT_FOR_SOURCE["simulated_expert"], doctor)
    # For simulated points, case_id holds the photo's row number in final_field_val, so none is used twice.
    used = {p["case_id"] for p in db.calibration_points() if p["source"] == "simulated_expert"}
    fresh = [i for i in range(len(y)) if i not in used]
    pick = np.random.default_rng(seed).choice(fresh, size=min(k, len(fresh)), replace=False) if fresh else []
    db.add_calibration_points([("simulated_expert", int(i), int(y[i]), list(logits[i])) for i in pick])
    return recalibrate(doctor, note=f"{len(pick)} simulated expert labels")
