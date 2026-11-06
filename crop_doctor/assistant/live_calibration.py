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

import os
from pathlib import Path

import numpy as np

from crop_doctor import config
from crop_doctor.app import db
from crop_doctor.model.crops import crops_from_labels, mask_logits
from crop_doctor.uncertainty.calibration import fit_temperature, softmax
from crop_doctor.uncertainty.conformal import (
    evaluate_sets, group_prediction_sets, group_quantiles, uniform_noise,
)
from crop_doctor.model.crops import crop_of

ALPHA = 0.1
LAB = "lab_val"
FIELD_SOURCES = ("field_cal", "expert_audit", "simulated_expert")
# Which data splits feed calibration. Comes from the app config ("splits"); default = the v1 model's splits.
DEFAULT_SPLITS = {"dir": "crop_doctor/data/splits", "lab": "lab_val", "cal": "final_field_cal",
                  "simulate": "final_field_val", "monitor": "field_test"}


def splits(doctor) -> dict:
    return {**DEFAULT_SPLITS, **(getattr(doctor, "cfg", {}) or {}).get("splits", {})}


def split_for_source(doctor, source: str) -> str:
    s = splits(doctor)
    return {"lab_val": s["lab"], "field_cal": s["cal"], "simulated_expert": s["simulate"]}[source]


def cache_dir(doctor) -> Path:
    """Cached model outputs per split. The live server ships these files (it has no datasets or PyTorch).
    Locally the cache is per model, so switching models never reuses another model's outputs."""
    env = os.environ.get("CROP_DOCTOR_LOGITS_DIR")
    if env:
        return Path(env)
    cfg = getattr(doctor, "cfg", {}) or {}
    tag = Path(cfg.get("checkpoint") or cfg.get("onnx") or "model").stem
    return config.OUTPUTS_DIR / "live_logits" / tag


def split_logits(split: str, doctor) -> tuple[np.ndarray, np.ndarray]:
    """Crop-masked logits of the app's model on a split (computed once, then cached on disk)."""
    path = cache_dir(doctor) / f"{split}.npz"
    if path.exists():
        d = np.load(path)
        return d["logits"], d["labels"]
    import pandas as pd
    from torch.utils.data import DataLoader

    from crop_doctor.model.common import FrameDataset, eval_transform
    from crop_doctor.model.train_final import logits_of
    df = pd.read_csv(config.ROOT / splits(doctor)["dir"] / f"{split}.csv")
    y = df["label_idx"].to_numpy()
    dl = DataLoader(FrameDataset(df, eval_transform()), batch_size=64, num_workers=0)
    logits = mask_logits(logits_of(doctor.model, dl, doctor.dev), doctor.classes, crops_from_labels(y, doctor.classes))
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(path, logits=logits, labels=y)
    return logits, y


def calibration_set(points: list[dict]) -> tuple[np.ndarray, np.ndarray, int]:
    field = [p for p in points if p["source"] in FIELD_SOURCES]
    use = field if field else [p for p in points if p["source"] == LAB]
    if not use:
        return np.zeros((0, 0)), np.zeros(0, dtype=int), 0
    return np.array([p["logits"] for p in use]), np.array([p["label_idx"] for p in use]), len(field)


def fit(logits: np.ndarray, labels: np.ndarray, doctor_classes: list[str]) -> tuple[float, dict]:
    if len(labels) == 0:
        return 1.0, {c: float("inf") for c in sorted({crop_of(c) for c in doctor_classes})}
    t = fit_temperature(logits, labels)
    # Mondrian conformal: one threshold per crop, each from that crop's calibration photos only.
    crops = np.array([crop_of(doctor_classes[y]) for y in labels])
    qhat = group_quantiles(softmax(logits, t), labels, crops, ALPHA, uniform_noise(len(labels), 7))
    return t, {c: qhat.get(c, float("inf")) for c in sorted({crop_of(c) for c in doctor_classes})}


def recalibrate(doctor, note: str = "") -> dict:
    """Recompute T and q-hat from the stored points, apply them to the app, measure on the monitor set."""
    points = db.calibration_points()
    logits, labels, n_field = calibration_set(points)
    t, qhat = fit(logits, labels, doctor.classes)
    doctor.set_calibration(t, qhat)
    mon_logits, mon_y = split_logits(splits(doctor)["monitor"], doctor)
    mon_crops = np.array([crop_of(doctor.classes[y]) for y in mon_y])
    sets = group_prediction_sets(softmax(mon_logits, t), qhat, mon_crops, uniform_noise(len(mon_y), 12345))
    m = evaluate_sets(sets, mon_y)
    run = {"n_points": len(labels), "n_field_points": n_field, "temperature": t, "qhat": max(qhat.values()),
           "qhat_by_crop": qhat,
           "monitor_coverage": m["coverage"], "monitor_set_size": m["avg_set_size"],
           "monitor_answered": m["answered_rate"], "note": note}
    db.add_calibration_run(run)
    return run


def reset(doctor, base: str) -> dict:
    """base='field' (normal: start from the 95 field calibration photos) or 'lab' (demo: lab photos only)."""
    db.clear_calibration_points()
    source = "field_cal" if base == "field" else "lab_val"
    logits, y = split_logits(split_for_source(doctor, source), doctor)
    db.add_calibration_points([(source, None, int(yy), list(lg)) for lg, yy in zip(logits, y)])
    return recalibrate(doctor, note=f"reset to {base} calibration")


def ensure_initialised(doctor) -> dict:
    """First start: no points yet -> field calibration. Otherwise reapply the latest settings."""
    runs = db.calibration_runs()
    if not db.calibration_points():
        return reset(doctor, "field")
    last = runs[-1] if runs else recalibrate(doctor, note="startup")
    doctor.set_calibration(last["temperature"], db.run_qhat(last))
    return last


def add_expert_label(doctor, case: dict, label: str) -> dict | None:
    """Expert labelled a RANDOM AUDIT case -> becomes a calibration point -> recalibrate now."""
    if not case.get("audit") or label not in doctor.classes:
        return None
    from PIL import Image
    import io
    probs_logits = doctor.logits(Image.open(io.BytesIO(db.load_image(case["image_path"]))), case["crop"])
    db.add_calibration_points([("expert_audit", case["id"], doctor.classes.index(label), list(probs_logits))])
    return recalibrate(doctor, note=f"expert audit label (case {case['id']})")


def simulate_expert_labels(doctor, k: int, seed: int) -> dict:
    """Demo: k random photos from the "simulate" split (field_val: not used for training or calibration) arrive with labels."""
    logits, y = split_logits(split_for_source(doctor, "simulated_expert"), doctor)
    # For simulated points, case_id holds the photo's row number in that split, so none is used twice.
    used = {p["case_id"] for p in db.calibration_points() if p["source"] == "simulated_expert"}
    fresh = [i for i in range(len(y)) if i not in used]
    pick = np.random.default_rng(seed).choice(fresh, size=min(k, len(fresh)), replace=False) if fresh else []
    db.add_calibration_points([("simulated_expert", int(i), int(y[i]), list(logits[i])) for i in pick])
    return recalibrate(doctor, note=f"{len(pick)} simulated expert labels")
