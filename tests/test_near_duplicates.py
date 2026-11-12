"""Near-duplicate audit (crop_doctor/data/near_duplicates.py) on synthetic photos: a resized, re-saved, rotated copy
is found and confirmed; a different photo is not."""
from __future__ import annotations

import numpy as np
from PIL import Image

from crop_doctor.data.near_duplicates import best_corr, confirmed_pairs, thumbnail
from crop_doctor.data.prepare_v3 import dhashes


def _photo(seed: int) -> Image.Image:
    """A smooth random 'photo' (blurred noise), so resizing keeps its structure like a real picture."""
    small = np.random.default_rng(seed).integers(0, 256, (12, 12, 3), dtype=np.uint8)
    return Image.fromarray(small).resize((300, 300), Image.BICUBIC)


def test_resized_rotated_copy_is_a_confirmed_twin_and_other_photo_is_not(tmp_path):
    orig, other = tmp_path / "orig.png", tmp_path / "other.png"
    twin = tmp_path / "twin.jpg"
    _photo(1).save(orig)
    _photo(2).save(other)
    _photo(1).resize((180, 180)).rotate(90, expand=True).save(twin, quality=70)   # web copy: smaller, JPEG, turned

    H = np.array([dhashes(p) for p in (orig, other, twin)])
    pairs = confirmed_pairs([twin], H[2:], [orig, other], H[:2])
    assert [p["r"] for p in pairs if p["confirmed"]] == [0]           # matches the original only

    assert best_corr(thumbnail(twin), thumbnail(orig)) > 0.9
    assert best_corr(thumbnail(other), thumbnail(orig)) < 0.9
