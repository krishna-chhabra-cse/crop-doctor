"""Run once during the Render build: expand the 16-bit model weights into a plain 32-bit ONNX file.

    python -m server.build_assets

The repo stores the model with 16-bit weights (56 MB, under GitHub's 100 MB file limit). Expanding them at
build time means the running server loads a ready-to-use file, using far less memory than expanding on startup.
Also pre-downloads the small text-embedding model so the first farmer question isn't slow.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from crop_doctor.model.backends import _upcast_w16


def main() -> None:
    cfg_path = Path(os.environ.get("CROP_DOCTOR_APP_CONFIG", "server/assets/app_model.json"))
    cfg = json.loads(cfg_path.read_text())
    src = cfg_path.parent / cfg["onnx"]
    if src.stem.endswith("_w16"):
        out = src.with_name(src.stem[:-4] + "_fp32.onnx")
        out.write_bytes(_upcast_w16(src))
        print(f"expanded {src.name} -> {out.name} ({out.stat().st_size / 1e6:.0f} MB)")
    try:
        from crop_doctor.knowledge.rag import MiniLMOnnx
        MiniLMOnnx()
        print("embedding model cached")
    except Exception as e:  # noqa: BLE001 - not fatal: the server falls back to keyword search
        print(f"embedding model not cached: {e}")


if __name__ == "__main__":
    main()
