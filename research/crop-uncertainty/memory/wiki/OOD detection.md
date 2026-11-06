# OOD detection

- **The model's top confidence score is a decent first warning sign that it is wrong, though not a perfect one.** (w2-04)
  - Claim: Maximum softmax probability is a simple baseline signal for detecting misclassified and out-of-distribution inputs, since correct predictions tend to get higher max-softmax scores, but it can be outperformed.
  - Source: https://arxiv.org/abs/1610.02136
  - For our project: Use max-softmax as the default abstention score and measure its misclassification-detection AUROC on field photos; compare against ensemble/MC-dropout uncertainty.
- **If the model's top guess has low confidence, that is a cheap first warning that the photo may be wrong or unfamiliar.** (w4-01)
  - Claim: Maximum softmax probability (MSP) is the standard baseline for flagging both misclassified and out-of-distribution inputs, because correct predictions tend to have higher max softmax, but the authors note it can be beaten.
  - Source: https://arxiv.org/abs/1610.02136
  - For our project: Implement MSP as the zero-cost baseline 'I'm not sure' score that every other method must beat.
- **The same 'strangeness' score that flags unfamiliar photos can be plugged into conformal prediction to give guaranteed-rate warnings.** (w4-08)
  - Claim: OOD scores can be used as non-conformity scores in conformal prediction, and conformal prediction can correct overly optimistic finite-sample OOD evaluation metrics.
  - Source: https://arxiv.org/abs/2403.11532
  - For our project: Calibrate the OOD threshold conformally on a small expert-labelled field set so the false-alarm rate on known diseases is controlled; report finite-sample uncertainty on FPR95.

Related: [[conformal prediction]], [[Hendrycks & Gimpel 2017]], [[max softmax probability]], [[maximum softmax probability]], [[misclassification detection]], [[non-conformity score]]
