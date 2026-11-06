"""The full assistant pipeline for one photo: quality gate -> model -> shortlist -> decision -> severity -> urgency.

    python -m crop_doctor.assistant.pipeline path/to/leaf.jpg --crop tomato
    python -m crop_doctor.assistant.pipeline leaf.jpg --crop tomato --extent many
    python -m crop_doctor.assistant.pipeline leaf.jpg --crop tomato --question rings_vs_small_spots --option 1 --seed 42

The returned dict is what the chat app (Day 7) shows and what the LLM (Day 6) turns into a friendly reply.
The LLM never changes the diagnosis: it only explains it.
"""
from __future__ import annotations

import argparse
import json
import secrets

import numpy as np
import torch
from PIL import Image

from crop_doctor import config
from crop_doctor.assistant.decision import disease_name, decide, knowledge, urgency
from crop_doctor.model.common import device, eval_transform, load_trained_model
from crop_doctor.model.crops import crop_mask
from crop_doctor.uncertainty.calibration import softmax
from crop_doctor.vision_extras import quality_gate, severity

APP_CONFIG = config.OUTPUTS_DIR / "app_model.json"


class CropDoctor:
    def __init__(self, alpha: float = 0.1, dev: torch.device | None = None):
        cfg = json.loads(APP_CONFIG.read_text())
        self.dev = dev or device()
        self.model, self.classes = load_trained_model(self.dev, config.OUTPUTS_DIR / cfg["checkpoint"])
        self.temperature = cfg["temperature"]
        self.qhat = cfg["qhat"][str(alpha)]
        self.alpha = alpha
        self.crops = sorted({knowledge()["diseases"][c]["crop"] for c in self.classes})
        self.tf = eval_transform()

    def set_calibration(self, temperature: float, qhat: float) -> None:
        """Live recalibration (expert labels) swaps these two numbers; the network is untouched."""
        self.temperature, self.qhat = float(temperature), float(qhat)

    @torch.no_grad()
    def logits(self, img: Image.Image, crop: str) -> np.ndarray:
        x = self.tf(img.convert("RGB")).unsqueeze(0).to(self.dev)
        out = self.model(x).float().cpu().numpy()[0].astype(np.float64)
        out[~crop_mask(self.classes, crop)] = -np.inf          # the farmer told us the crop
        return out

    def probabilities(self, img: Image.Image, crop: str) -> np.ndarray:
        return softmax(self.logits(img, crop)[None, :], self.temperature)[0]

    def assess(self, img: Image.Image, crop: str, extent: str | None = None, question_id: str | None = None,
               option: int | None = None, seed: int | None = None) -> dict:
        if crop not in self.crops:
            raise ValueError(f"crop must be one of {self.crops}")
        seed = secrets.randbelow(2**31) if seed is None else seed   # randomised APS noise; kept so a follow-up answer reuses it
        result = {"crop": crop, "seed": seed, "alpha": self.alpha}

        gate = quality_gate.check(img)
        result["quality"] = {"ok": gate.ok, "problems": gate.problems, "metrics": gate.metrics}
        if not gate.ok:
            return {**result, "status": "retake", "message": gate.message}

        probs = self.probabilities(img, crop)
        u = float(np.random.default_rng(seed).uniform())
        answer, asked = None, set()
        if question_id is not None:
            q = next(q for q in knowledge()["follow_up_questions"] if q["id"] == question_id)
            answer = {"question_id": question_id, "favours": q["options"][option]["favours"]}
            asked = {question_id}
        result.update(decide(probs, self.classes, self.qhat, u, answer=answer, asked=asked))

        if result["status"] == "diagnosis":
            sev = severity.estimate(img)
            result["severity_estimate"] = sev
            result["urgency"] = urgency(result["label"], extent, sev["band"])
            result["disease"] = knowledge()["diseases"][result["label"]]
            if extent is None:
                result["ask_extent"] = knowledge()["extent_question"]
        result["message"] = summary_message(result)
        return result


def summary_message(r: dict) -> str:
    """Plain template text. The LLM (Day 6) rewrites this in friendlier words and adds sourced treatment."""
    s = r["status"]
    if s == "healthy":
        return "Your leaf looks healthy. Keep checking your plants every few days."
    if s == "diagnosis":
        u = r["urgency"]
        sev = r["severity_estimate"]
        sev_txt = f" About {sev['fraction']:.0%} of the leaf looks damaged (estimate)." if sev["fraction"] is not None else ""
        return (f"Most likely: {disease_name(r['label'])} ({r['probability']:.0%} likely).{sev_txt} "
                f"Act within {u['act_within']}. {u['why']} Please confirm with a local expert before spraying.")
    if s == "question":
        names = ", ".join(disease_name(c) for c in r["shortlist"])
        return f"It could be: {names}. One question to tell them apart: {r['question']['question']}"
    if s == "expert":
        names = ", ".join(disease_name(c) for c in r["shortlist"][:3])
        possible = f" Possible: {names}." if names else ""
        return f"I'm not sure ({r['reason']}).{possible} I've sent your photo to an expert, who will reply soon."
    return r.get("message", "")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--crop", required=True)
    ap.add_argument("--extent", choices=["few", "some", "many"])
    ap.add_argument("--question")
    ap.add_argument("--option", type=int)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--alpha", type=float, default=0.1)
    a = ap.parse_args()
    doc = CropDoctor(alpha=a.alpha)
    r = doc.assess(Image.open(a.image), a.crop, a.extent, a.question, a.option, a.seed)
    r.pop("disease", None)
    print(json.dumps(r, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
