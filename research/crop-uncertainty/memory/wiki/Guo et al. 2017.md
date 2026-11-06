# Guo et al. 2017

- **A network that says it is 95% sure is often right much less than 95% of the time, but dividing its scores by one tuned number largely fixes this on familiar data.** (w2-01)
  - Claim: Modern deep CNNs are poorly calibrated (overconfident), and single-parameter temperature scaling fitted on a held-out validation set is a simple, effective post-hoc fix on in-distribution data.
  - Source: https://arxiv.org/abs/1706.04599
  - For our project: Report ECE and reliability diagrams before/after temperature scaling as our baseline calibration step, fitting T on a lab (PlantVillage-style) validation split.

Related: [[calibration]], [[ECE]], [[temperature scaling]]
