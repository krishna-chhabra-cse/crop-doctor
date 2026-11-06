"""Pick the demo photos shown under "Try a sample", using the CURRENT app model.

    python -m crop_doctor.app.make_samples

One real held-out field photo per kind of answer (clear tomato case, clear potato case, needs a question,
unclear -> expert, healthy tomato, healthy potato), plus a deliberately blurred photo (asks to retake).
Each sample stores the seed that produces its outcome, so demos are repeatable.
"""
from __future__ import annotations

import json
import os

import pandas as pd
from PIL import Image, ImageFilter

from crop_doctor import config
from crop_doctor.assistant.pipeline import CropDoctor
from crop_doctor.model.crops import crop_of

OUT = config.ROOT / "crop_doctor" / "app" / "samples"
WANT = {
    "diag_tomato": "Tomato leaf (clear case)",
    "diag_potato": "Potato leaf (clear case)",
    "question": "Leaf that needs one question",
    "expert": "Unclear leaf (goes to an expert)",
    "healthy_tomato": "Healthy tomato leaf",
    "healthy_potato": "Healthy potato leaf",
}


def kind_of(r: dict, label: str) -> str | None:
    s = r["status"]
    if s == "diagnosis" and r["label"] == label and r["probability"] > 0.85:
        return "diag_potato" if label.startswith("potato") else "diag_tomato"
    if s == "question" and label in r["shortlist"]:
        return "question"
    if s == "expert" and len(r["shortlist"]) >= 3:
        return "expert"
    if s == "healthy" and r["label"] == label:
        return f"healthy_{crop_of(label)}"
    return None


def main() -> None:
    doc = CropDoctor()
    cfg = json.loads((config.OUTPUTS_DIR / "app_model.json").read_text())
    split_dir = config.ROOT / cfg.get("splits", {}).get("dir", "crop_doctor/data/splits")
    test = pd.read_csv(split_dir / "field_test.csv").sample(frac=1, random_state=3)
    found: dict[str, dict] = {}
    for i, (path, label) in enumerate(zip(test["path"], test["label"])):
        img = Image.open(config.DATASETS_DIR / path)
        if min(img.size) < 400:
            continue                                    # demo photos should look good on screen
        k = kind_of(doc.assess(img, crop_of(label), seed=i), label)
        if k and k not in found:
            found[k] = {"path": path, "label": label, "seed": i}
        if len(found) == len(WANT):
            break
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("*.jpg"):
        old.unlink()
    index = []
    for k, title in WANT.items():
        if k not in found:
            print(f"  no photo found for: {title}")
            continue
        v = found[k]
        img = Image.open(config.DATASETS_DIR / v["path"]).convert("RGB")
        img.thumbnail((900, 900))
        img.save(OUT / f"{k}.jpg", quality=88)
        status = doc.assess(Image.open(OUT / f"{k}.jpg"), crop_of(v["label"]), seed=v["seed"])["status"]
        index.append({"file": f"{k}.jpg", "title": title, "crop": crop_of(v["label"]), "true_label": v["label"],
                      "seed": v["seed"], "expected_status": status, "source": v["path"]})
        print(f"  {title}: {v['label']} -> {status}")
    base = next(s for s in index if s["file"].startswith("diag_"))
    Image.open(OUT / base["file"]).filter(ImageFilter.GaussianBlur(9)).save(OUT / "retake_blurry.jpg", quality=88)
    index.append({**base, "file": "retake_blurry.jpg", "title": "Blurry photo (asks to retake)",
                  "expected_status": "retake", "source": base["source"] + " (blurred on purpose)"})
    (OUT / "samples.json").write_text(json.dumps(index, indent=2))
    print(f"wrote {len(index)} samples to {os.path.relpath(OUT)}")


if __name__ == "__main__":
    main()
