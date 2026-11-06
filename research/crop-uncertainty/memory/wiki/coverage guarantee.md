# coverage guarantee

- **Instead of one guess, the model gives a short list of possible diseases and promises the right one is in the list, say, 90% of the time, as long as new photos look like the photos used to set it up.** (w3-01)
  - Claim: Split conformal prediction wraps any pre-trained classifier to output label sets that contain the true label with a user-chosen probability, with finite-sample, distribution-free validity that rests on calibration and test data being exchangeable.
  - Source: https://arxiv.org/abs/2107.07511
  - For our project: Use split conformal on top of our trained classifier as the 'I'm not sure' mechanism: a set with more than one disease means defer to the expert; the guarantee only holds if the calibration photos come from the same distribution as deployment photos.

Related: [[Angelopoulos & Bates]], [[conformal prediction]], [[exchangeability]]
