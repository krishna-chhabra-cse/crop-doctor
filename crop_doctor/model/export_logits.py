"""Run the trained model once over every split and save its raw outputs (logits).

    python -m crop_doctor.model.export_logits

Writes crop_doctor/outputs/logits_<split>.npz with arrays: logits, labels, paths.
All later experiments (calibration, abstention, conformal) read these files, so they
never need the GPU and every experiment uses exactly the same model outputs.
"""
from __future__ import annotations

import argparse

import numpy as np
import torch
from torch.utils.data import DataLoader

from crop_doctor import config
from crop_doctor.model.common import SplitDataset, device, eval_transform, load_trained_model

SPLITS = ["lab_val", "lab_test", "field_pool", "field_test"]  # lab_train not needed: the model saw it


@torch.no_grad()
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    dev = device()
    model, classes = load_trained_model(dev)
    print(f"{'split':<12}{'images':>8}{'accuracy':>10}")
    for split in SPLITS:
        ds = SplitDataset(split, eval_transform())
        dl = DataLoader(ds, batch_size=64, shuffle=False, num_workers=args.workers)
        outs = []
        for x, _ in dl:
            outs.append(model(x.to(dev)).float().cpu())
        logits = torch.cat(outs).numpy()
        labels = ds.df["label_idx"].to_numpy()
        np.savez_compressed(config.OUTPUTS_DIR / f"logits_{split}.npz", logits=logits, labels=labels,
                            paths=ds.df["path"].to_numpy(), classes=np.array(classes))
        acc = (logits.argmax(1) == labels).mean()
        print(f"{split:<12}{len(labels):>8}{acc:>10.3f}")


if __name__ == "__main__":
    main()
