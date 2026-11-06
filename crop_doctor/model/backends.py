"""Two interchangeable ways to run the image model. Both return raw logits for one photo.

- TorchBackend: PyTorch + GPU. Used for training, experiments and local development.
- OnnxBackend:  ONNX Runtime on CPU, no PyTorch. Used on the live server (Render free plan: 512 MB RAM).
  The model is exported once to ONNX and its weights are quantised to 8-bit integers (about 4x smaller).
  export_onnx.py checks that both backends agree on the field test photos before the file is used.

The ONNX path needs its own preprocessing (no torchvision), written to match torchvision's
Resize(256) -> CenterCrop(224) -> ToTensor -> Normalize exactly.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

IMG_SIZE = 224
RESIZE = int(IMG_SIZE * 256 / 224)
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess(img: Image.Image) -> np.ndarray:
    """PIL photo -> (1, 3, 224, 224) float32, identical to the torchvision eval transform."""
    img = img.convert("RGB")
    w, h = img.size
    if w <= h:                                   # torchvision: shorter side -> RESIZE, keep aspect ratio
        nw, nh = RESIZE, int(RESIZE * h / w)
    else:
        nw, nh = int(RESIZE * w / h), RESIZE
    img = img.resize((nw, nh), Image.BILINEAR)
    left = int(round((nw - IMG_SIZE) / 2.0))
    top = int(round((nh - IMG_SIZE) / 2.0))
    img = img.crop((left, top, left + IMG_SIZE, top + IMG_SIZE))
    x = (np.asarray(img, dtype=np.float32) / 255.0 - MEAN) / STD
    return x.transpose(2, 0, 1)[None].astype(np.float32)


def _upcast_w16(path: Path) -> bytes:
    """Weights were stored as 16-bit floats to halve the file; turn them back into 32-bit floats in memory."""
    import onnx
    from onnx import numpy_helper
    m = onnx.load(str(path))
    for init in m.graph.initializer:
        if init.data_type == onnx.TensorProto.FLOAT16:
            init.CopyFrom(numpy_helper.from_array(numpy_helper.to_array(init).astype(np.float32), init.name))
    return m.SerializeToString()


class OnnxBackend:
    def __init__(self, model_path: Path, classes: list[str], threads: int = 2):
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = threads       # small server: don't oversubscribe the CPU
        opts.enable_cpu_mem_arena = False         # don't keep a big memory pool: the free server has 512 MB
        opts.enable_mem_pattern = False
        source: str | bytes = str(model_path)
        if Path(model_path).stem.endswith("_w16"):
            built = Path(model_path).with_name(Path(model_path).stem[:-4] + "_fp32.onnx")
            if built.exists():                    # expanded once at build time (server/build_assets.py)
                source = str(built)
            else:
                source = _upcast_w16(Path(model_path))
        self.session = ort.InferenceSession(source, opts, providers=["CPUExecutionProvider"])
        del source
        self.input_name = self.session.get_inputs()[0].name
        self.classes = classes

    def raw_logits(self, img: Image.Image) -> np.ndarray:
        return self.session.run(None, {self.input_name: preprocess(img)})[0][0].astype(np.float64)


class TorchBackend:
    def __init__(self, checkpoint: Path, dev=None):
        import torch

        from crop_doctor.model.common import device, eval_transform, load_trained_model
        self.torch = torch
        self.dev = dev or device()
        self.model, self.classes = load_trained_model(self.dev, checkpoint)
        self.tf = eval_transform()

    def raw_logits(self, img: Image.Image) -> np.ndarray:
        with self.torch.no_grad():
            x = self.tf(img.convert("RGB")).unsqueeze(0).to(self.dev)
            return self.model(x).float().cpu().numpy()[0].astype(np.float64)


def load_backend(app_config: Path, prefer: str = "auto"):
    """app_config: JSON with 'checkpoint' (PyTorch .pt) and/or 'onnx' (file names next to it) and 'classes'."""
    cfg = json.loads(Path(app_config).read_text())
    base = Path(app_config).parent
    use_onnx = prefer == "onnx" or (prefer == "auto" and not (base / cfg.get("checkpoint", "-")).exists())
    if use_onnx:
        return OnnxBackend(base / cfg["onnx"], cfg["classes"])
    return TorchBackend(base / cfg["checkpoint"])
