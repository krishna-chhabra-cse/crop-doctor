"""Download only the tomato + potato folders of PlantVillage and PlantDoc.

PlantVillage: git "partial clone + sparse checkout" fetches only the folders we ask
for, instead of the full 2 GB repository.
PlantDoc: downloaded as one zip and only our folders are extracted.

    python -m crop_doctor.data.download

Works the same on a laptop and in Google Colab (Day 2).
"""
from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from crop_doctor.config import CLASS_MAP, PLANTDOC_DIR, PLANTVILLAGE_DIR

PLANTVILLAGE_REPO = "https://github.com/spMohanty/PlantVillage-Dataset.git"
PLANTDOC_ZIP = "https://codeload.github.com/pratikkayal/PlantDoc-Dataset/zip/refs/heads/master"


def sparse_clone(repo: str, dest: Path, folders: list[str]) -> None:
    if (dest / ".git").exists():
        print(f"{dest.name}: already downloaded, skipping")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"{dest.name}: cloning {len(folders)} folders from {repo}")
    subprocess.run(
        ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse", repo, str(dest)], check=True
    )
    # --no-cone lets us list exact folder paths (folder names contain spaces).
    subprocess.run(["git", "-C", str(dest), "sparse-checkout", "set", "--no-cone", *folders], check=True)


def safe_name(name: str) -> str:
    """Some PlantDoc files are named like 'IMG_1629.JPG?1507122477.jpg'.
    '?' and similar characters are illegal in Windows file names, so replace them."""
    return re.sub(r'[<>:"|?*]', "_", name)


def download_zip_folders(zip_url: str, dest: Path, folders: list[str]) -> None:
    """Download a GitHub repo as one zip and extract only `folders` (paths inside the repo)."""
    if dest.exists() and any(dest.iterdir()):
        print(f"{dest.name}: already downloaded, skipping")
        return
    print(f"{dest.name}: downloading {zip_url} (about 1 GB, a few minutes) ...")
    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / "repo.zip"
        with urllib.request.urlopen(zip_url) as resp, open(zip_path, "wb") as out:
            shutil.copyfileobj(resp, out, length=1 << 20)
        wanted = tuple(f.strip("/") + "/" for f in folders)
        n = 0
        with zipfile.ZipFile(zip_path) as zf:
            for info in zf.infolist():
                # Zip entries look like "PlantDoc-Dataset-master/train/Tomato leaf/x.jpg": drop the top folder.
                inner = info.filename.split("/", 1)[-1]
                if info.is_dir() or not inner.startswith(wanted):
                    continue
                target = dest.joinpath(*(safe_name(part) for part in inner.split("/")))
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(target, "wb") as out:
                    shutil.copyfileobj(src, out)
                n += 1
    print(f"{dest.name}: extracted {n} files")


def main() -> None:
    pv_folders = [f"/raw/color/{pv}/" for pv, _ in CLASS_MAP.values()]
    pd_folders = [f"{split}/{pd}" for _, pd in CLASS_MAP.values() for split in ("train", "test")]
    sparse_clone(PLANTVILLAGE_REPO, PLANTVILLAGE_DIR, pv_folders)
    # PlantDoc via zip, not git: git refuses to check out its '?' file names on Windows.
    download_zip_folders(PLANTDOC_ZIP, PLANTDOC_DIR, pd_folders)
    print("done")


if __name__ == "__main__":
    main()
