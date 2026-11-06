# domain shift

- **When the new photos look different from the training photos, the model's 'I'm unsure' signal is unreliable, so using it alone to pick photos for experts can be worse than picking at random.** (w5-02)
  - Claim: Under domain shift, entropy-based uncertainty sampling frequently underperforms random sampling because target-domain uncertainty is miscalibrated, while CLUE (uncertainty-weighted clustering) gives modest consistent gains.
  - Source: https://arxiv.org/abs/2010.08666
  - For our project: Include random sampling as a mandatory baseline and try a CLUE-style (uncertain AND diverse) selector for choosing which field photos the expert labels.

Related: [[active domain adaptation]], [[calibration]], [[CLUE]], [[uncertainty sampling]]
