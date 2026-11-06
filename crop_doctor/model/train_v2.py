"""Train the v2 app model on the bigger v2 dataset (11 classes, incl. healthy potato).

    python -m crop_doctor.model.train_v2                 # ~20-25 min on an RTX 3050
    python -m crop_doctor.model.train_v2 --smoke         # 1-minute code check

What "training properly" means here:
- Every batch mixes LAB photos (40%) and FIELD photos (60%), so the model learns from both worlds.
- Inside each group, classes are balanced with square-root weights: a class with 4x fewer photos is drawn
  2x more often per photo. Full 1/n balancing would repeat a 16-photo class hundreds of times (overfitting).
- Strong augmentation (crops, rotation, lighting, blur) to mimic phone photos.
- AdamW + one-cycle learning-rate schedule with warm-up; mixed precision on the GPU.
- The best epoch is chosen by MACRO-F1 on field_val (every class counts equally), never on a test set.

v3 (Exp 10, outlier exposure): the same recipe on splits_v3, which adds a 12th class "tomato_something_else":

    python -m crop_doctor.model.train_v2 --splits splits_v3 --tag final_v3_convnext_tiny

If the splits folder has other_train.csv / other_val.csv, those photos join the FIELD training group / the
validation set (so the best epoch is chosen by 12-class macro-F1). v2 has neither file, so v2 is unchanged.
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import f1_score
from torch.utils.data import ConcatDataset, DataLoader, WeightedRandomSampler

from crop_doctor import config
from crop_doctor.model.common import IMG_SIZE, FrameDataset, build_model, device, eval_transform
from crop_doctor.model.crops import crops_from_labels, mask_logits
from crop_doctor.model.train import set_seed
from crop_doctor.model.train_final import logits_of, strong_train_transform

SPLITS_ROOT = config.ROOT / "crop_doctor" / "data"
ARCH = "convnext_tiny.fb_in22k_ft_in1k"
LAB_SHARE = 0.4


def sqrt_balanced(labels: pd.Series, total_weight: float) -> np.ndarray:
    counts = labels.map(labels.value_counts())
    w = 1.0 / np.sqrt(counts.to_numpy(dtype=float))
    return w / w.sum() * total_weight


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--samples-per-epoch", type=int, default=16000)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--splits", default="splits_v2", help="folder under crop_doctor/data/")
    ap.add_argument("--tag", default="final_v2_convnext_tiny", help="checkpoint name in crop_doctor/outputs/")
    args = ap.parse_args()
    if args.smoke:
        args.epochs, args.samples_per_epoch = 1, 256

    set_seed(config.SEED)
    dev = device()
    splits = SPLITS_ROOT / args.splits
    classes = json.loads((splits / "classes.json").read_text())
    lab = pd.read_csv(splits / "lab_train.csv")
    field = pd.read_csv(splits / "field_train.csv")
    val = pd.read_csv(splits / "field_val.csv")
    if (splits / "other_train.csv").exists():          # v3: "something else" photos (outlier exposure)
        field = pd.concat([field, pd.read_csv(splits / "other_train.csv")], ignore_index=True)
    if (splits / "other_val.csv").exists():
        val = pd.concat([val, pd.read_csv(splits / "other_val.csv")], ignore_index=True)
    if args.smoke:
        val = val.sample(64, random_state=0)

    tf = strong_train_transform()
    train_ds = ConcatDataset([FrameDataset(lab, tf), FrameDataset(field, tf)])
    weights = np.concatenate([sqrt_balanced(lab["label"], LAB_SHARE), sqrt_balanced(field["label"], 1 - LAB_SHARE)])
    sampler = WeightedRandomSampler(torch.as_tensor(weights), num_samples=args.samples_per_epoch, replacement=True,
                                    generator=torch.Generator().manual_seed(config.SEED))
    kw = dict(num_workers=args.workers, pin_memory=dev.type == "cuda", persistent_workers=args.workers > 0)
    train_dl = DataLoader(train_ds, batch_size=args.batch_size, sampler=sampler, drop_last=True, **kw)
    val_dl = DataLoader(FrameDataset(val, eval_transform()), batch_size=64, **kw)
    val_y = val["label_idx"].to_numpy()
    val_crops = crops_from_labels(val_y, classes)

    model = build_model(len(classes), arch=ARCH).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.05)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=args.lr, total_steps=args.epochs * len(train_dl), pct_start=0.1)
    scaler = torch.amp.GradScaler(enabled=dev.type == "cuda")
    loss_fn = torch.nn.CrossEntropyLoss()

    tag = args.tag + ("_smoke" if args.smoke else "")
    ckpt = config.OUTPUTS_DIR / f"{tag}.pt"
    best, log = -1.0, []
    print(f"lab {len(lab)} + field {len(field)} train photos ({field['source'].value_counts().to_dict()}), "
          f"val {len(val)}, {args.epochs} epochs x {len(train_dl)} steps", flush=True)
    for epoch in range(1, args.epochs + 1):
        model.train()
        t0, running, seen = time.time(), 0.0, 0
        for x, y in train_dl:
            x, y = x.to(dev, non_blocking=True), y.to(dev, non_blocking=True)
            with torch.autocast(device_type=dev.type, enabled=dev.type == "cuda"):
                loss = loss_fn(model(x), y)
            opt.zero_grad(set_to_none=True)
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sched.step()
            running += loss.item() * len(y)
            seen += len(y)
        vl = mask_logits(logits_of(model, val_dl, dev), classes, val_crops)
        pred = vl.argmax(1)
        f1 = float(f1_score(val_y, pred, average="macro"))
        per_source = {s: round(float((pred == val_y)[val["source"].to_numpy() == s].mean()), 4)
                      for s in val["source"].unique()}
        entry = {"epoch": epoch, "train_loss": round(running / seen, 4), "val_macro_f1": round(f1, 4),
                 "val_acc": round(float((pred == val_y).mean()), 4), "val_acc_by_source": per_source,
                 "seconds": round(time.time() - t0, 1)}
        log.append(entry)
        print(entry, flush=True)
        if f1 > best:
            best = f1
            torch.save({"state_dict": model.state_dict(), "classes": classes, "arch": ARCH, "img_size": IMG_SIZE,
                        "epoch": epoch, "val_macro_f1": f1}, ckpt)
    (config.OUTPUTS_DIR / f"{tag}_log.json").write_text(json.dumps({"args": vars(args), "epochs": log}, indent=2))
    print(f"best field_val macro-F1 {best:.4f}; saved {ckpt}", flush=True)


if __name__ == "__main__":
    main()
