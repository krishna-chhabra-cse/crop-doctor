"""Experiment 6: the whole assistant on unseen field photos, as a farmer would use it.

    python -m crop_doctor.experiments.exp6_pipeline

For every field_test photo: quality gate -> model -> shortlist -> decision. When the assistant asks a
follow-up question, a SIMULATED farmer answers:
  - careful farmer: always picks the option that matches the true disease (an upper bound)
  - typical farmer: right 80% of the time, otherwise picks another option at random
(If no option matches the true disease, both pick at random.)

Also checks the two colour tools on real photos:
  - quality gate pass rate on lab and field photos (should be high: those photos are usable)
  - severity estimate: does it score healthy leaves lower than diseased ones? (AUROC)
"""
from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd
from PIL import Image
from sklearn.metrics import roc_auc_score

from crop_doctor import config
from crop_doctor.assistant.pipeline import CropDoctor
from crop_doctor.experiments.common import save_metrics
from crop_doctor.model.crops import crop_of
from crop_doctor.vision_extras import quality_gate, severity

FARMERS = {"careful": 1.0, "typical": 0.8}


def farmer_option(question: dict, true_label: str, accuracy: float, rng) -> int:
    options = question["options"]
    right = [i for i, o in enumerate(options) if true_label in o["favours"]]
    if right and rng.uniform() < accuracy:
        return right[0]
    wrong = [i for i in range(len(options)) if i not in right] or list(range(len(options)))
    return int(rng.choice(wrong))


def run_assistant(doc: CropDoctor, test: pd.DataFrame) -> dict:
    out = {}
    for farmer, acc in FARMERS.items():
        rng = np.random.default_rng(0)
        rows = []
        for i, (path, label) in enumerate(zip(test["path"], test["label"])):
            img = Image.open(config.DATASETS_DIR / path)
            r = doc.assess(img, crop_of(label), seed=i)
            asked = r["status"] == "question"
            if asked:
                opt = farmer_option(r["question"], label, acc, rng)
                r = doc.assess(img, crop_of(label), question_id=r["question"]["id"], option=opt, seed=i)
            rows.append({"status": r["status"], "asked": asked, "label": r.get("label"),
                         "correct": r.get("label") == label if r["status"] in ("diagnosis", "healthy") else None})
        df = pd.DataFrame(rows)
        answered = df[df["status"].isin(["diagnosis", "healthy"])]
        out[farmer] = {
            "photos": len(df),
            "status_share": {k: round(v / len(df), 4) for k, v in Counter(df["status"]).items()},
            "asked_a_question": round(float(df["asked"].mean()), 4),
            "answered_by_assistant": round(len(answered) / len(df), 4),
            "accuracy_when_answered": round(float(answered["correct"].mean()), 4),
            "accuracy_answered_directly": round(float(answered[~answered["asked"]]["correct"].mean()), 4),
            "accuracy_answered_after_question": (round(float(answered[answered["asked"]]["correct"].mean()), 4)
                                                 if answered["asked"].any() else None),
            "questions_resolved": (round(float(answered["asked"].sum() / max(df["asked"].sum(), 1)), 4)),
            "sent_to_expert": round(float((df["status"] == "expert").mean()), 4),
        }
    return out


def check_tools() -> dict:
    res = {}
    for split in ("lab_test", "field_test"):
        df = pd.read_csv(config.SPLITS_DIR / f"{split}.csv")
        gate_ok, sev, healthy = [], [], []
        for path, label in zip(df["path"], df["label"]):
            img = Image.open(config.DATASETS_DIR / path)
            gate_ok.append(quality_gate.check(img).ok)
            s = severity.estimate(img)["fraction"]
            if s is not None and label.startswith("tomato"):   # healthy vs diseased: tomato only (no potato healthy)
                sev.append(s)
                healthy.append(label == "tomato_healthy")
        sev, healthy = np.array(sev), np.array(healthy)
        res[split] = {"gate_pass_rate": round(float(np.mean(gate_ok)), 4),
                      "severity_median_healthy": round(float(np.median(sev[healthy])), 3),
                      "severity_median_diseased": round(float(np.median(sev[~healthy])), 3),
                      "severity_auroc_diseased_vs_healthy": round(float(roc_auc_score(~healthy, sev)), 3)}
    return res


def main() -> None:
    doc = CropDoctor(alpha=0.1)
    # The test split of whichever model the app uses (v2: PlantDoc + Tanzania held-out field photos).
    split_dir = config.ROOT / doc.cfg.get("splits", {}).get("dir", "crop_doctor/data/splits")
    test = pd.read_csv(split_dir / "field_test.csv")
    res = {"assistant_on_field_test": run_assistant(doc, test), "tools": check_tools()}
    save_metrics("exp6_pipeline", res)
    for farmer, r in res["assistant_on_field_test"].items():
        print(f"  {farmer} farmer: statuses {r['status_share']}")
        print(f"     answered by assistant {r['answered_by_assistant']:.1%} (accuracy {r['accuracy_when_answered']:.1%}; "
              f"direct {r['accuracy_answered_directly']:.1%}, after question {r['accuracy_answered_after_question']}) | "
              f"asked {r['asked_a_question']:.1%}, resolved {r['questions_resolved']:.1%} | expert {r['sent_to_expert']:.1%}")
    for split, t in res["tools"].items():
        print(f"  {split}: gate pass {t['gate_pass_rate']:.1%} | severity healthy {t['severity_median_healthy']:.2f} vs "
              f"diseased {t['severity_median_diseased']:.2f}, AUROC {t['severity_auroc_diseased_vs_healthy']:.2f}")


if __name__ == "__main__":
    main()
