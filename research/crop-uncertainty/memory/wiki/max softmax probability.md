# max softmax probability

- **If the model's top guess has low confidence, that is a cheap first warning that the photo may be wrong or unfamiliar.** (w4-01)
  - Claim: Maximum softmax probability (MSP) is the standard baseline for flagging both misclassified and out-of-distribution inputs, because correct predictions tend to have higher max softmax, but the authors note it can be beaten.
  - Source: https://arxiv.org/abs/1610.02136
  - For our project: Implement MSP as the zero-cost baseline 'I'm not sure' score that every other method must beat.
- **A slightly different formula on the same model outputs catches noticeably more unfamiliar photos than plain confidence.** (w4-02)
  - Claim: The energy score (logsumexp of logits) is a drop-in post-hoc replacement for softmax confidence that reduces average FPR@TPR95 by 18.03% on a CIFAR-10 WideResNet.
  - Source: https://arxiv.org/abs/2010.03759
  - For our project: Compute energy alongside MSP from the same logits (one line of code) for the OOD test on non-leaf / other-crop photos.

Related: [[energy score]], [[FPR95]], [[misclassification detection]], [[OOD detection]]
