"""Train the FINAL model used by the app: lab photos + expert-labelled field photos, stronger augmentation.

    python -m crop_doctor.model.train_final --arch efficientnet_b0
    python -m crop_doctor.model.train_final --arch convnext_tiny.fb_in22k_ft_in1k
    python -m crop_doctor.model.train_final --arch efficientnet_b0 --smoke

Day 4 showed expert labels must also be used for retraining to make the assistant useful. Here we
use the whole field_pool (the "expert labels collected so far"), split into three parts:
  final_field_train (60%)  -> training, mixed with lab photos (~30% of every batch is field)
  final_field_val   (20%)  -> choosing between candidate models
  final_field_cal   (20%)  -> temperature + conformal calibration for the app
field_test stays untouched: it is used ONCE, at the very end, to report results (exp5_final_model.py).

Every checkpoint is judged on final_field_val with crop known (the app asks the farmer the crop).
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from torch.utils.data import ConcatDataset, DataLoader, WeightedRandomSampler
from torchvision import transforms

from crop_doctor import config
from crop_doctor.model.common import IMG_SIZE, MEAN, STD, FrameDataset, build_model, device, eval_transform, load_classes
from crop_doctor.model.crops import crops_from_labels, mask_logits
from crop_doctor.model.train import set_seed
from crop_doctor.uncertainty.calibration import nll, softmax

FIELD_SHARE = 0.3  # share of each batch drawn from field photos
ARCH_DEFAULTS = {  # learning rate, batch size (fits a 6 GB GPU with mixed precision)
    "efficientnet_b0": (3e-4, 48),
    "convnext_tiny.fb_in22k_ft_in1k": (1e-4, 32),
}


def final_splits() -> dict[str, pd.DataFrame]:
    """Deterministically split field_pool 60/20/20, stratified by class; saved as CSVs for the record."""
    names = ["final_field_train", "final_field_val", "final_field_cal"]
    paths = {n: config.SPLITS_DIR / f"{n}.csv" for n in names}
    if all(p.exists() for p in paths.values()):
        return {n: pd.read_csv(p) for n, p in paths.items()}
    pool = pd.read_csv(config.SPLITS_DIR / "field_pool.csv")
    train, rest = train_test_split(pool, train_size=0.6, stratify=pool["label"], random_state=config.SEED)
    val, cal = train_test_split(rest, train_size=0.5, stratify=rest["label"], random_state=config.SEED)
    out = {"final_field_train": train, "final_field_val": val, "final_field_cal": cal}
    for n, df in out.items():
        df.to_csv(paths[n], index=False)
    return out


def strong_train_transform() -> transforms.Compose:
    # Stronger than Day 2 on purpose: now the goal is field performance, not measuring the gap.
    # Tighter crops, rotations, lighting changes and blur mimic hand-held phone photos.
    return transforms.Compose([
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.3, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(25),
        transforms.ColorJitter(0.35, 0.35, 0.35, 0.05),
        transforms.RandomApply([transforms.GaussianBlur(5, sigma=(0.1, 2.0))], p=0.25),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])


@torch.no_grad()
def logits_of(model, loader, dev) -> np.ndarray:
    model.eval()
    out = []
    for x, _ in loader:
        with torch.autocast(device_type=dev.type, enabled=dev.type == "cuda"):
            out.append(model(x.to(dev)).float().cpu())
    return torch.cat(out).numpy().astype(np.float64)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arch", default="efficientnet_b0", choices=list(ARCH_DEFAULTS))
    ap.add_argument("--epochs", type=int, default=4)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--smoke", action="store_true", help="tiny run to check the code")
    args = ap.parse_args()
    lr, batch = ARCH_DEFAULTS[args.arch]
    set_seed(config.SEED)
    dev = device()
    classes = load_classes()
    splits = final_splits()

    lab = pd.read_csv(config.SPLITS_DIR / "lab_train.csv")
    field = splits["final_field_train"]
    val = splits["final_field_val"]
    if args.smoke:
        lab, args.epochs = lab.sample(300, random_state=0), 1

    train_ds = ConcatDataset([FrameDataset(lab, strong_train_transform()), FrameDataset(field, strong_train_transform())])
    # Sampling weights: all lab photos together get 70% of the draws, all field photos 30%.
    weights = np.concatenate([np.full(len(lab), (1 - FIELD_SHARE) / len(lab)), np.full(len(field), FIELD_SHARE / len(field))])
    sampler = WeightedRandomSampler(torch.as_tensor(weights), num_samples=len(lab), replacement=True,
                                    generator=torch.Generator().manual_seed(config.SEED))
    kw = dict(num_workers=args.workers, pin_memory=dev.type == "cuda", persistent_workers=args.workers > 0)
    train_dl = DataLoader(train_ds, batch_size=batch, sampler=sampler, drop_last=True, **kw)
    val_dl = DataLoader(FrameDataset(val, eval_transform()), batch_size=64, **kw)
    val_y = val["label_idx"].to_numpy()
    val_crops = crops_from_labels(val_y, classes)

    model = build_model(len(classes), arch=args.arch).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.05)
    sched = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=args.epochs * len(train_dl), pct_start=0.1)
    scaler = torch.amp.GradScaler(enabled=dev.type == "cuda")
    loss_fn = torch.nn.CrossEntropyLoss()

    tag = args.arch.split(".")[0] + ("_smoke" if args.smoke else "")
    ckpt_path = config.OUTPUTS_DIR / f"final_{tag}.pt"
    log, best = [], -1.0
    print(f"{args.arch}: lab {len(lab)} + field {len(field)} photos, val {len(val)}, batch {batch}, lr {lr}", flush=True)
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
        acc = float((vl.argmax(1) == val_y).mean())
        entry = {"epoch": epoch, "train_loss": round(running / seen, 4), "field_val_acc_crop_known": round(acc, 4),
                 "field_val_nll": round(nll(softmax(vl), val_y), 4), "seconds": round(time.time() - t0, 1)}
        log.append(entry)
        print(entry, flush=True)
        if acc > best:
            best = acc
            torch.save({"state_dict": model.state_dict(), "classes": classes, "arch": args.arch, "img_size": IMG_SIZE,
                        "epoch": epoch, "field_val_acc_crop_known": acc}, ckpt_path)
    (config.OUTPUTS_DIR / f"final_{tag}_log.json").write_text(json.dumps({"args": vars(args), "epochs": log}, indent=2))
    print(f"best field_val accuracy (crop known) {best:.4f}; saved {ckpt_path}", flush=True)


if __name__ == "__main__":
    main()
