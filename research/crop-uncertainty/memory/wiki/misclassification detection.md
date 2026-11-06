# misclassification detection

- **The model's top confidence score is a decent first warning sign that it is wrong, though not a perfect one.** (w2-04)
  - Claim: Maximum softmax probability is a simple baseline signal for detecting misclassified and out-of-distribution inputs, since correct predictions tend to get higher max-softmax scores, but it can be outperformed.
  - Source: https://arxiv.org/abs/1610.02136
  - For our project: Use max-softmax as the default abstention score and measure its misclassification-detection AUROC on field photos; compare against ensemble/MC-dropout uncertainty.
- **If the model's top guess has low confidence, that is a cheap first warning that the photo may be wrong or unfamiliar.** (w4-01)
  - Claim: Maximum softmax probability (MSP) is the standard baseline for flagging both misclassified and out-of-distribution inputs, because correct predictions tend to have higher max softmax, but the authors note it can be beaten.
  - Source: https://arxiv.org/abs/1610.02136
  - For our project: Implement MSP as the zero-cost baseline 'I'm not sure' score that every other method must beat.
- **The best alarm for 'this is not a leaf at all' is not the same as the best alarm for 'I probably got this disease wrong'.** (w4-04)
  - Claim: Misclassification detection and OOD detection need different scores: OOD detectors evaluated for selective classification with OOD data rank differently and generally fail to beat the softmax baseline.
  - Source: https://arxiv.org/abs/2207.07506
  - For our project: Report two separate evaluations: AURC/accuracy-vs-coverage on field photos (use MSP) and AUROC/FPR95 for unknown photos (use energy/KNN); possibly combine both scores.

Related: [[energy score]], [[Hendrycks & Gimpel 2017]], [[max softmax probability]], [[maximum softmax probability]], [[OOD detection]], [[selective classification]], [[SIRC]]
