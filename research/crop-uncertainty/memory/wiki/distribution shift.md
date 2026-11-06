# distribution shift

- **A medical study found the 90% promise silently failed on photos from new hospitals, and was only fixed by re-tuning on about 1,000 expert-labelled photos from the new hospital.** (w3-04)
  - Claim: In medical imaging, conformal coverage breaks under input and label distribution shift, but recalibrating on about 1,000 labelled target-domain images restored the guarantee; it is also unreliable per-class and of limited value with few classes.
  - Source: https://arxiv.org/abs/2506.18162
  - For our project: Directly frames our 'how many expert labels' question: run a sweep of target calibration sizes (e.g. 25-1000 field photos) and measure when lab-calibrated vs field-recalibrated coverage reaches 90%; also report per-class coverage.
- **Each time the expert confirms or corrects a case, the system nudges how cautious it is, so over time it keeps its 90% promise even as conditions change.** (w3-05)
  - Claim: Adaptive conformal inference (Gibbs & Candes 2021) keeps long-run coverage under arbitrary, changing distribution shift by continually updating one threshold parameter online as labelled feedback arrives.
  - Source: https://arxiv.org/abs/2106.00170
  - For our project: Natural fit for expert-in-the-loop: simulate a stream of field photos where each expert label updates the threshold; guarantee is long-run average, not per-photo, so state that limitation.

Related: [[ACI]], [[adaptive conformal inference]], [[class-conditional coverage]], [[conformal prediction]], [[Mehrtens et al. 2025]], [[online learning]], [[recalibration]]
