# weighted conformal

- **If field photos differ from lab photos, you can give more weight to lab examples that look field-like, using unlabelled field photos to decide the weights.** (w3-03)
  - Claim: Weighted conformal prediction restores coverage under covariate shift by reweighting calibration points with the test/train likelihood ratio, which can be estimated from unlabelled target inputs.
  - Source: https://arxiv.org/abs/1904.06019
  - For our project: Optional baseline: train a lab-vs-field domain classifier on unlabelled field photos to get weights; but lab-to-field is not pure covariate shift (labels and class mix also change), so treat it as a comparison, not the main fix.

Related: [[covariate shift]], [[exchangeability]], [[Tibshirani et al. 2019]]
