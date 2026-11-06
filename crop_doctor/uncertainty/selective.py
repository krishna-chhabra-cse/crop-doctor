"""Selective prediction: answer only when sure, otherwise say "I'm not sure".

Coverage = fraction of photos the model answers.
Risk     = fraction of those answers that are wrong.
Sorting photos from most to least confident and answering only the top k gives one
(coverage, risk) point per k: the risk-coverage curve. A good "confidence" signal puts
the wrong answers at the bottom, so risk falls quickly as coverage shrinks.
"""
from __future__ import annotations

import numpy as np


def risk_coverage(confidence: np.ndarray, correct: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (coverage, risk) arrays for answering the k most confident photos, k = 1..n."""
    order = np.argsort(-confidence, kind="stable")
    errors = np.cumsum(~correct[order])
    k = np.arange(1, len(confidence) + 1)
    return k / len(confidence), errors / k


def aurc(confidence: np.ndarray, correct: np.ndarray) -> float:
    """Area under the risk-coverage curve (average risk over all coverage levels). Lower is better."""
    _, risk = risk_coverage(confidence, correct)
    return float(risk.mean())


def oracle_aurc(correct: np.ndarray) -> float:
    """Best possible AURC for this accuracy: a perfect signal ranks every right answer above every wrong one."""
    return aurc(correct.astype(float), correct)


def risk_at_coverage(confidence: np.ndarray, correct: np.ndarray, coverage: float) -> float:
    cov, risk = risk_coverage(confidence, correct)
    return float(risk[max(int(np.ceil(coverage * len(cov))) - 1, 0)])


def threshold_for_risk(confidence: np.ndarray, correct: np.ndarray, target_risk: float) -> float:
    """Lowest confidence threshold whose answered set has risk <= target_risk (on the photos given).
    Returns +inf if even the single most confident answer is wrong."""
    order = np.argsort(-confidence, kind="stable")
    _, risk = risk_coverage(confidence, correct)
    ok = np.nonzero(risk <= target_risk)[0]
    return float(confidence[order][ok[-1]]) if len(ok) else float("inf")


def apply_threshold(confidence: np.ndarray, correct: np.ndarray, threshold: float) -> dict[str, float]:
    answered = confidence >= threshold
    cov = float(answered.mean())
    risk = float((~correct[answered]).mean()) if answered.any() else 0.0
    return {"threshold": round(threshold, 4), "coverage": round(cov, 4), "risk": round(risk, 4)}
