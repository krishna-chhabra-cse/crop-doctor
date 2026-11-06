"""Fine-tune EfficientNet-B0 on PlantVillage (lab photos only).

    python -m crop_doctor.model.train                 # full run (~5 epochs)
    python -m crop_doctor.model.train --limit 256 --epochs 1   # 1-minute smoke test

Field photos are NOT used here. The model learns from lab photos only, which is
exactly the situation we want to study (lab-trained model meets real farm photos).

Saves the best epoch (by lab_val accuracy) to crop_doctor/outputs/model.pt and a
per-epoch log to crop_doctor/outputs/train_log.json.
"""
from __future__ import annotations

import argparse
import json
import random
import time

import numpy as np
import torch
from torch.utils.data import DataLoader

from crop_doctor import config
from crop_doctor.model.common import (
    ARCH, CHECKPOINT, IMG_SIZE, SplitDataset, build_model, device, eval_transform, load_classes, train_transform,
)


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


@torch.no_grad()
def evaluate(model, loader, dev) -> float:
    model.eval()
    correct = total = 0
    for x, y in loader:
        x, y = x.to(dev, non_blocking=True), y.to(dev, non_blocking=True)
        with torch.autocast(device_type=dev.type, enabled=dev.type == "cuda"):
            logits = model(x)
        correct += (logits.argmax(1) == y).sum().item()
        total += len(y)
    return correct / total


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--batch-size", type=int, default=48)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None, help="use only N images per split (smoke test)")
    args = ap.parse_args()

    set_seed(config.SEED)
    dev = device()
    classes = load_classes()
    print(f"device: {dev} ({torch.cuda.get_device_name(0) if dev.type == 'cuda' else 'cpu'}), classes: {len(classes)}")

    train_ds = SplitDataset("lab_train", train_transform(), args.limit)
    val_ds = SplitDataset("lab_val", eval_transform(), args.limit)
    loader_kw = dict(batch_size=args.batch_size, num_workers=args.workers, pin_memory=dev.type == "cuda",
                     persistent_workers=args.workers > 0)
    train_dl = DataLoader(train_ds, shuffle=True, drop_last=True, **loader_kw)
    val_dl = DataLoader(val_ds, shuffle=False, **loader_kw)

    model = build_model(len(classes)).to(dev)
    # Plain cross-entropy, no label smoothing: label smoothing changes the model's confidence,
    # and we want to measure calibration of a standard model.
    loss_fn = torch.nn.CrossEntropyLoss()
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs * len(train_dl))
    scaler = torch.amp.GradScaler(enabled=dev.type == "cuda")  # mixed precision: faster, less GPU memory

    log, best_acc = [], -1.0
    config.OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    for epoch in range(1, args.epochs + 1):
        model.train()
        t0, running, seen = time.time(), 0.0, 0
        for step, (x, y) in enumerate(train_dl, 1):
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
            if step % 50 == 0:
                print(f"  epoch {epoch} step {step}/{len(train_dl)} loss {running / seen:.4f}", flush=True)
        val_acc = evaluate(model, val_dl, dev)
        entry = {"epoch": epoch, "train_loss": round(running / seen, 4), "val_acc": round(val_acc, 4),
                 "seconds": round(time.time() - t0, 1)}
        log.append(entry)
        print(entry, flush=True)
        if val_acc > best_acc:  # keep the best epoch, judged on lab validation only
            best_acc = val_acc
            torch.save({"state_dict": model.state_dict(), "classes": classes, "arch": ARCH, "img_size": IMG_SIZE,
                        "epoch": epoch, "val_acc": val_acc, "args": vars(args)}, CHECKPOINT)

    (config.OUTPUTS_DIR / "train_log.json").write_text(json.dumps({"args": vars(args), "epochs": log}, indent=2))
    print(f"best lab_val accuracy {best_acc:.4f}; saved {CHECKPOINT}")


if __name__ == "__main__":
    main()
