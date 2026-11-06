"""Single source of truth for classes, paths and seeds.

Every other module imports from here, so changing a class or a path happens in one place.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # the "ML project" folder
DATASETS_DIR = ROOT / "datasets"                       # raw downloads (git-ignored, large)
PLANTVILLAGE_DIR = DATASETS_DIR / "plantvillage"
PLANTDOC_DIR = DATASETS_DIR / "plantdoc"
SPLITS_DIR = ROOT / "crop_doctor" / "data" / "splits"  # small CSVs: these ARE the dataset definition
OUTPUTS_DIR = ROOT / "crop_doctor" / "outputs"

SEED = 42

# Our label -> (PlantVillage folder under raw/color, PlantDoc folder under train/ and test/).
# Only diseases that exist in BOTH datasets: the model trains on lab photos (PlantVillage)
# and is judged on field photos (PlantDoc) of the same diseases.
CLASS_MAP: dict[str, tuple[str, str]] = {
    "tomato_bacterial_spot":    ("Tomato___Bacterial_spot", "Tomato leaf bacterial spot"),
    "tomato_early_blight":      ("Tomato___Early_blight", "Tomato Early blight leaf"),
    "tomato_late_blight":       ("Tomato___Late_blight", "Tomato leaf late blight"),
    "tomato_leaf_mold":         ("Tomato___Leaf_Mold", "Tomato mold leaf"),
    "tomato_septoria":          ("Tomato___Septoria_leaf_spot", "Tomato Septoria leaf spot"),
    "tomato_spider_mites":      ("Tomato___Spider_mites Two-spotted_spider_mite", "Tomato two spotted spider mites leaf"),
    "tomato_yellow_curl_virus": ("Tomato___Tomato_Yellow_Leaf_Curl_Virus", "Tomato leaf yellow virus"),
    "tomato_mosaic_virus":      ("Tomato___Tomato_mosaic_virus", "Tomato leaf mosaic virus"),
    "tomato_healthy":           ("Tomato___healthy", "Tomato leaf"),
    "potato_early_blight":      ("Potato___Early_blight", "Potato leaf early blight"),
    "potato_late_blight":       ("Potato___Late_blight", "Potato leaf late blight"),
}

# A class needs at least this many field photos, otherwise its field results are just noise.
MIN_FIELD_IMAGES = 15

# PlantVillage: 80% train / 10% val / 10% test.  PlantDoc: 50% expert pool / 50% field test.
LAB_SPLIT = {"lab_train": 0.8, "lab_val": 0.1, "lab_test": 0.1}
FIELD_POOL_FRACTION = 0.5

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
