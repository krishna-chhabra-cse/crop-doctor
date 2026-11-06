# energy score

- **A slightly different formula on the same model outputs catches noticeably more unfamiliar photos than plain confidence.** (w4-02)
  - Claim: The energy score (logsumexp of logits) is a drop-in post-hoc replacement for softmax confidence that reduces average FPR@TPR95 by 18.03% on a CIFAR-10 WideResNet.
  - Source: https://arxiv.org/abs/2010.03759
  - For our project: Compute energy alongside MSP from the same logits (one line of code) for the OOD test on non-leaf / other-crop photos.
- **The best alarm for 'this is not a leaf at all' is not the same as the best alarm for 'I probably got this disease wrong'.** (w4-04)
  - Claim: Misclassification detection and OOD detection need different scores: OOD detectors evaluated for selective classification with OOD data rank differently and generally fail to beat the softmax baseline.
  - Source: https://arxiv.org/abs/2207.07506
  - For our project: Report two separate evaluations: AURC/accuracy-vs-coverage on field photos (use MSP) and AUROC/FPR95 for unknown photos (use energy/KNN); possibly combine both scores.

Related: [[FPR95]], [[max softmax probability]], [[misclassification detection]], [[selective classification]], [[SIRC]]
