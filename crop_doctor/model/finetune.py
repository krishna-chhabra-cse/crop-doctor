"""Retrain the lab model on a few expert-labelled field photos ("learning from experts").

Each training batch is half field photos (the new expert labels) and half lab photos ("replay").
The lab half stops the model from forgetting what it learned from 13k lab photos while it adapts
to a handful of field photos (otherwise it would just memorise them: "catastrophic forgetting").

Images are decoded once and kept in memory, so the many short retraining runs in Exp 4 are fast.
"""
from __future__ import annotations

import copy

import numpy as np
import pandas as pd
import torch
from PIL import Image
from torchvision import transforms

from crop_doctor import config
from crop_doctor.model.common import IMG_SIZE, eval_transform, train_transform

PRE_RESIZE = transforms.Resize(int(IMG_SIZE * 256 / 224))  # same first step as eval_transform


def load_images(df: pd.DataFrame) -> list[Image.Image]:
    """Decode and shrink every image once (short side 256 px); keeps RAM use small."""
    out = []
    for p in df["path"]:
        with Image.open(config.DATASETS_DIR / p) as im:
            out.append(PRE_RESIZE(im.convert("RGB")))
    return out


def to_eval_tensor(images: list[Image.Image]) -> torch.Tensor:
    tf = eval_transform()
    return torch.stack([tf(im) for im in images]).half()


@torch.no_grad()
def predict_logits(model: torch.nn.Module, x: torch.Tensor, dev: torch.device, batch: int = 128) -> np.ndarray:
    model.eval()
    outs = []
    for i in range(0, len(x), batch):
        xb = x[i:i + batch].to(dev).float()
        with torch.autocast(device_type=dev.type, enabled=dev.type == "cuda"):
            outs.append(model(xb).float().cpu())
    return torch.cat(outs).numpy().astype(np.float64)


def finetune(base_model: torch.nn.Module, field_imgs: list[Image.Image], field_labels: np.ndarray,
             lab_imgs: list[Image.Image], lab_labels: np.ndarray, dev: torch.device, *,
             steps: int = 150, batch: int = 32, lr: float = 1e-4, seed: int = 0) -> torch.nn.Module:
    """Return a COPY of base_model fine-tuned for a fixed number of steps (same compute for every budget)."""
    model = copy.deepcopy(base_model).to(dev)
    if len(field_imgs) == 0:
        return model.eval()
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)
    tf = train_transform()
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    loss_fn = torch.nn.CrossEntropyLoss()
    scaler = torch.amp.GradScaler(enabled=dev.type == "cuda")
    half = batch // 2
    model.train()
    for _ in range(steps):
        fi = rng.integers(0, len(field_imgs), half)   # sample with replacement: works even for 5 photos
        li = rng.integers(0, len(lab_imgs), batch - half)
        x = torch.stack([tf(field_imgs[i]) for i in fi] + [tf(lab_imgs[i]) for i in li]).to(dev)
        y = torch.as_tensor(np.concatenate([field_labels[fi], lab_labels[li]]), device=dev)
        with torch.autocast(device_type=dev.type, enabled=dev.type == "cuda"):
            loss = loss_fn(model(x), y)
        opt.zero_grad(set_to_none=True)
        scaler.scale(loss).backward()
        scaler.step(opt)
        scaler.update()
    return model.eval()
