# conformal prediction

- **Nobody we found has measured how often a crop-disease app can safely say 'not sure' on real field photos, so that is open ground.** (w2-06)
  - Claim: The grape-leaf field study measured calibration only and did not evaluate abstention, rejection thresholds, or risk-coverage, and searches found no plant-disease paper reporting risk-coverage or conformal coverage on field photos (conformal work in plants targets species ID, e.g. Pl@ntNet).
  - Source: https://arxiv.org/abs/2507.06867
  - For our project: Our contribution: risk-coverage/AURC under lab-to-field shift for crop disease, plus how many expert-labelled field images restore a target coverage at fixed error.
- **Instead of one guess, the model gives a short list of possible diseases and promises the right one is in the list, say, 90% of the time, as long as new photos look like the photos used to set it up.** (w3-01)
  - Claim: Split conformal prediction wraps any pre-trained classifier to output label sets that contain the true label with a user-chosen probability, with finite-sample, distribution-free validity that rests on calibration and test data being exchangeable.
  - Source: https://arxiv.org/abs/2107.07511
  - For our project: Use split conformal on top of our trained classifier as the 'I'm not sure' mechanism: a set with more than one disease means defer to the expert; the guarantee only holds if the calibration photos come from the same distribution as deployment photos.
- **There are ready-made recipes for building these 'shortlists'; one (RAPS) is tuned to keep the shortlist short so it stays useful.** (w3-02)
  - Claim: APS (Romano et al. 2020) and RAPS (Angelopoulos et al. 2021) are the standard prediction-set scores for image classifiers; RAPS adds regularisation to keep sets small while preserving coverage.
  - Source: https://arxiv.org/abs/2009.14193
  - For our project: Compare APS vs RAPS (plus simple LAC/threshold score) on field photos, reporting both empirical coverage and average set size, since set size drives how many cases go to the expert.
- **A medical study found the 90% promise silently failed on photos from new hospitals, and was only fixed by re-tuning on about 1,000 expert-labelled photos from the new hospital.** (w3-04)
  - Claim: In medical imaging, conformal coverage breaks under input and label distribution shift, but recalibrating on about 1,000 labelled target-domain images restored the guarantee; it is also unreliable per-class and of limited value with few classes.
  - Source: https://arxiv.org/abs/2506.18162
  - For our project: Directly frames our 'how many expert labels' question: run a sweep of target calibration sizes (e.g. 25-1000 field photos) and measure when lab-calibrated vs field-recalibrated coverage reaches 90%; also report per-class coverage.
- **The same 'strangeness' score that flags unfamiliar photos can be plugged into conformal prediction to give guaranteed-rate warnings.** (w4-08)
  - Claim: OOD scores can be used as non-conformity scores in conformal prediction, and conformal prediction can correct overly optimistic finite-sample OOD evaluation metrics.
  - Source: https://arxiv.org/abs/2403.11532
  - For our project: Calibrate the OOD threshold conformally on a small expert-labelled field set so the false-alarm rate on known diseases is controlled; report finite-sample uncertainty on FPR95.

Related: [[Angelopoulos & Bates]], [[APS]], [[class-conditional coverage]], [[coverage guarantee]], [[distribution shift]], [[exchangeability]], [[https---arxiv.org-abs-2006.02544]], [[Mehrtens et al. 2025]], [[non-conformity score]], [[OOD detection]], [[Pl@ntNet]], [[plant disease]], [[RAPS]], [[recalibration]], [[risk-coverage curve]], [[selective classification]]
