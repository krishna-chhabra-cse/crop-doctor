# class-conditional coverage

- **A medical study found the 90% promise silently failed on photos from new hospitals, and was only fixed by re-tuning on about 1,000 expert-labelled photos from the new hospital.** (w3-04)
  - Claim: In medical imaging, conformal coverage breaks under input and label distribution shift, but recalibrating on about 1,000 labelled target-domain images restored the guarantee; it is also unreliable per-class and of limited value with few classes.
  - Source: https://arxiv.org/abs/2506.18162
  - For our project: Directly frames our 'how many expert labels' question: run a sweep of target calibration sizes (e.g. 25-1000 field photos) and measure when lab-calibrated vs field-recalibrated coverage reaches 90%; also report per-class coverage.

Related: [[conformal prediction]], [[distribution shift]], [[Mehrtens et al. 2025]], [[recalibration]]
