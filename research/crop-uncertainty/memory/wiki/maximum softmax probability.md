# maximum softmax probability

- **The model's top confidence score is a decent first warning sign that it is wrong, though not a perfect one.** (w2-04)
  - Claim: Maximum softmax probability is a simple baseline signal for detecting misclassified and out-of-distribution inputs, since correct predictions tend to get higher max-softmax scores, but it can be outperformed.
  - Source: https://arxiv.org/abs/1610.02136
  - For our project: Use max-softmax as the default abstention score and measure its misclassification-detection AUROC on field photos; compare against ensemble/MC-dropout uncertainty.

Related: [[Hendrycks & Gimpel 2017]], [[misclassification detection]], [[OOD detection]]
