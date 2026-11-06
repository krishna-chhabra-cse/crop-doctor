# exchangeability

- **Instead of one guess, the model gives a short list of possible diseases and promises the right one is in the list, say, 90% of the time, as long as new photos look like the photos used to set it up.** (w3-01)
  - Claim: Split conformal prediction wraps any pre-trained classifier to output label sets that contain the true label with a user-chosen probability, with finite-sample, distribution-free validity that rests on calibration and test data being exchangeable.
  - Source: https://arxiv.org/abs/2107.07511
  - For our project: Use split conformal on top of our trained classifier as the 'I'm not sure' mechanism: a set with more than one disease means defer to the expert; the guarantee only holds if the calibration photos come from the same distribution as deployment photos.
- **If field photos differ from lab photos, you can give more weight to lab examples that look field-like, using unlabelled field photos to decide the weights.** (w3-03)
  - Claim: Weighted conformal prediction restores coverage under covariate shift by reweighting calibration points with the test/train likelihood ratio, which can be estimated from unlabelled target inputs.
  - Source: https://arxiv.org/abs/1904.06019
  - For our project: Optional baseline: train a lab-vs-field domain classifier on unlabelled field photos to get weights; but lab-to-field is not pure covariate shift (labels and class mix also change), so treat it as a comparison, not the main fix.

Related: [[Angelopoulos & Bates]], [[conformal prediction]], [[covariate shift]], [[coverage guarantee]], [[Tibshirani et al. 2019]], [[weighted conformal]]
