# noisy feedback

- **If the app learns from its own guesses (or unverified farmer confirmations), it can reinforce its own errors.** (w5-04)
  - Claim: Training on the model's own predictions (naive pseudo-labeling) overfits to its own mistakes due to confirmation bias, mitigated by soft labels, mixup and keeping a minimum number of truly labeled samples per mini-batch.
  - Source: https://arxiv.org/abs/1908.02983
  - For our project: Only retrain on expert-verified field labels; do not feed back the model's own confident predictions or farmer clicks without expert check, or if used, mix every batch with verified labels.

Related: [[confirmation bias]], [[pseudo-labeling]], [[self-training]]
