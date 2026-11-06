# non-conformity score

- **The same 'strangeness' score that flags unfamiliar photos can be plugged into conformal prediction to give guaranteed-rate warnings.** (w4-08)
  - Claim: OOD scores can be used as non-conformity scores in conformal prediction, and conformal prediction can correct overly optimistic finite-sample OOD evaluation metrics.
  - Source: https://arxiv.org/abs/2403.11532
  - For our project: Calibrate the OOD threshold conformally on a small expert-labelled field set so the false-alarm rate on known diseases is controlled; report finite-sample uncertainty on FPR95.

Related: [[conformal prediction]], [[OOD detection]]
