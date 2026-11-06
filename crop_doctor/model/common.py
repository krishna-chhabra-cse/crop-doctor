"""Shared pieces used by training, logit export and (later) the app.

Keeping the model definition and the image preprocessing in ONE place guarantees that
the app preprocesses a farmer's photo exactly like the test photos were preprocessed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import timm
import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms

from crop_doctor import config

ARCH = "efficientnet_b0"
IMG_SIZE = 224
# ImageNet statistics: the pretrained network expects inputs normalised this way.
MEAN = (0.485, 0.456, 0.406)
STD = (0.229, 0.224, 0.225)
CHECKPOINT = config.OUTPUTS_DIR / "model.pt"


def load_classes() -> list[str]:
    return json.loads((config.SPLITS_DIR / "classes.json").read_text())


def train_transform() -> transforms.Compose:
    # Standard, mild augmentation: random crop/zoom, flips, small colour changes.
    # Deliberately NOT designed to imitate field photos: we want to measure the honest lab->field gap.
    return transforms.Compose([
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.6, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.ColorJitter(0.2, 0.2, 0.2),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])


def eval_transform() -> transforms.Compose:
    # Deterministic: resize the short side, then take the centre square.
    return transforms.Compose([
        transforms.Resize(int(IMG_SIZE * 256 / 224)),
        transforms.CenterCrop(IMG_SIZE),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])


class SplitDataset(Dataset):
    """Reads one split CSV (e.g. lab_train.csv) and returns (image_tensor, label_idx)."""

    def __init__(self, split: str, transform, limit: int | None = None, seed: int = config.SEED):
        df = pd.read_csv(config.SPLITS_DIR / f"{split}.csv")
        if limit is not None and limit < len(df):
            df = df.sample(n=limit, random_state=seed)  # for quick smoke tests only
        self.df = df.reset_index(drop=True)
        self.transform = transform

    def __len__(self) -> int:
        return len(self.df)

    def __getitem__(self, i: int):
        row = self.df.iloc[i]
        with Image.open(config.DATASETS_DIR / row["path"]) as im:
            img = im.convert("RGB")
        return self.transform(img), int(row["label_idx"])


class FrameDataset(SplitDataset):
    """Same as SplitDataset, but from an in-memory DataFrame (used for the final model's field splits)."""

    def __init__(self, df: pd.DataFrame, transform):
        self.df = df.reset_index(drop=True)
        self.transform = transform


def build_model(num_classes: int, pretrained: bool = True, arch: str = ARCH) -> torch.nn.Module:
    # A pretrained ImageNet network; timm swaps the last layer for `num_classes` outputs.
    return timm.create_model(arch, pretrained=pretrained, num_classes=num_classes)


def load_trained_model(device: str | torch.device = "cpu", path=CHECKPOINT) -> tuple[torch.nn.Module, list[str]]:
    ckpt = torch.load(path, map_location=device)
    model = build_model(len(ckpt["classes"]), pretrained=False, arch=ckpt.get("arch", ARCH))
    model.load_state_dict(ckpt["state_dict"])
    return model.to(device).eval(), ckpt["classes"]


def device() -> torch.device:
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")
