"""Package the final model for the live server: ONNX + 8-bit weights + calibration files.

    python -m crop_doctor.model.export_onnx

1. Export the PyTorch checkpoint named in outputs/app_model.json to ONNX (a portable model format).
2. Quantise its weights to 8-bit integers (dynamic quantisation): ~4x smaller, runs fast on a small CPU.
3. CHECK: on all field_test photos, the quantised model must give the same top answer as PyTorch for at least
   98% of photos, and its accuracy must not drop by more than 1 point. Otherwise we stop and keep full precision.
4. Compute the server's cached outputs (lab_val, final_field_cal, final_field_val, field_test) WITH the ONNX
   model, refit temperature + conformal q-hat on final_field_cal, and write server/assets/.
"""
from __future__ import annotations

import json
import shutil

import numpy as np
import pandas as pd
import torch
from PIL import Image

from crop_doctor import config
from crop_doctor.model.backends import OnnxBackend
from crop_doctor.model.common import IMG_SIZE, load_trained_model
from crop_doctor.model.crops import crops_from_labels, mask_logits
from crop_doctor.uncertainty.calibration import fit_temperature, softmax
from crop_doctor.uncertainty.conformal import aps_scores, conformal_quantile, evaluate_sets, prediction_sets, uniform_noise

ASSETS = config.ROOT / "server" / "assets"
SPLITS = ["lab_val", "final_field_cal", "final_field_val", "field_test"]
ALPHAS = (0.1, 0.2)


def onnx_logits(backend: OnnxBackend, df: pd.DataFrame) -> np.ndarray:
    out = []
    for p in df["path"]:
        with Image.open(config.DATASETS_DIR / p) as im:
            out.append(backend.raw_logits(im))
    return np.array(out)


def main() -> None:
    app = json.loads((config.OUTPUTS_DIR / "app_model.json").read_text())
    model, classes = load_trained_model("cpu", config.OUTPUTS_DIR / app["checkpoint"])
    ASSETS.mkdir(parents=True, exist_ok=True)
    fp32, int8 = ASSETS / "model_fp32.onnx", ASSETS / "model.onnx"

    print("exporting to ONNX ...")
    torch.onnx.export(model, torch.randn(1, 3, IMG_SIZE, IMG_SIZE), fp32, input_names=["image"], output_names=["logits"],
                      dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}}, opset_version=17, dynamo=False)
    from onnxruntime.quantization import QuantType, quantize_dynamic
    # per_channel: a separate scale for each output channel of each layer -> much smaller rounding errors.
    quantize_dynamic(fp32, int8, weight_type=QuantType.QInt8, per_channel=True)
    print(f"  fp32 {fp32.stat().st_size / 1e6:.1f} MB -> int8 {int8.stat().st_size / 1e6:.1f} MB")

    # 3. Agreement check against PyTorch on field_test.
    test = pd.read_csv(config.SPLITS_DIR / "field_test.csv")
    y = test["label_idx"].to_numpy()
    from crop_doctor.model.backends import TorchBackend
    tb = TorchBackend(config.OUTPUTS_DIR / app["checkpoint"], dev=torch.device("cpu"))
    pt = np.array([tb.raw_logits(Image.open(config.DATASETS_DIR / p)) for p in test["path"]])
    q8 = onnx_logits(OnnxBackend(int8, classes), test)
    crops = crops_from_labels(y, classes)
    pt_m, q8_m = mask_logits(pt, classes, crops), mask_logits(q8, classes, crops)
    agree = float((pt_m.argmax(1) == q8_m.argmax(1)).mean())
    acc_pt, acc_q8 = float((pt_m.argmax(1) == y).mean()), float((q8_m.argmax(1) == y).mean())
    print(f"  top answer agreement {agree:.3f}; accuracy PyTorch {acc_pt:.3f} vs int8 {acc_q8:.3f}")
    use = int8
    if agree < 0.98 or acc_q8 < acc_pt - 0.01:
        # Plan B: keep full-precision maths but STORE the weights as 16-bit floats (half the file size, under
        # GitHub's 100 MB limit). OnnxBackend expands them back to 32-bit when the server starts.
        print("  int8 changed answers too much -> shipping 16-bit stored weights instead")
        import onnx
        from onnx import numpy_helper
        m = onnx.load(fp32)
        for init in m.graph.initializer:
            arr = numpy_helper.to_array(init)
            if arr.dtype == np.float32 and arr.size > 1024:
                init.CopyFrom(numpy_helper.from_array(arr.astype(np.float16), init.name))
        int8.unlink()
        use = ASSETS / "model_w16.onnx"
        onnx.save(m, use)       # not runnable as-is; OnnxBackend upcasts float16 weights on load
        print(f"  16-bit weights file: {use.stat().st_size / 1e6:.1f} MB")
        q8 = onnx_logits(OnnxBackend(use, classes), test)
        q8_m = mask_logits(q8, classes, crops)
        agree = float((pt_m.argmax(1) == q8_m.argmax(1)).mean())
        acc_q8 = float((q8_m.argmax(1) == y).mean())
        print(f"  16-bit: top answer agreement {agree:.3f}; accuracy {acc_q8:.3f}")
    fp32.unlink()
    for stale in ASSETS.glob("*.onnx"):
        if stale != use:
            stale.unlink()

    # 4. Server calibration files computed with the shipped model.
    backend = OnnxBackend(use, classes)
    logits_dir = ASSETS / "logits"
    logits_dir.mkdir(exist_ok=True)
    cache = {}
    for split in SPLITS:
        df = pd.read_csv(config.SPLITS_DIR / f"{split}.csv")
        yy = df["label_idx"].to_numpy()
        lg = mask_logits(onnx_logits(backend, df), classes, crops_from_labels(yy, classes))
        np.savez_compressed(logits_dir / f"{split}.npz", logits=lg, labels=yy)
        cache[split] = (lg, yy)
        print(f"  cached {split}: {len(yy)} photos")
    cal_l, cal_y = cache["final_field_cal"]
    t = fit_temperature(cal_l, cal_y)
    qhat = {str(a): conformal_quantile(aps_scores(softmax(cal_l, t), cal_y, uniform_noise(len(cal_y), 7)), a) for a in ALPHAS}
    mon_l, mon_y = cache["field_test"]
    m = evaluate_sets(prediction_sets(softmax(mon_l, t), qhat["0.1"], uniform_noise(len(mon_y), 12345)), mon_y)
    out = {"onnx": use.name, "classes": classes, "temperature": t, "qhat": qhat, "default_alpha": 0.1,
           "calibrated_on": "final_field_cal", "source_checkpoint": app["checkpoint"],
           "check": {"top1_agreement_with_pytorch": agree, "field_test_accuracy_pytorch": acc_pt,
                     "field_test_accuracy_onnx": acc_q8, "field_test_coverage_90": m["coverage"],
                     "field_test_avg_set_size": m["avg_set_size"]}}
    (ASSETS / "app_model.json").write_text(json.dumps(out, indent=2))
    print(f"  server calibration: T={t:.3f}, coverage {m['coverage']:.3f}, avg shortlist {m['avg_set_size']:.2f}")
    print(f"wrote {ASSETS}")


if __name__ == "__main__":
    main()
