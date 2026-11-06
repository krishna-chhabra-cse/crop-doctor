# FPR95

- **A slightly different formula on the same model outputs catches noticeably more unfamiliar photos than plain confidence.** (w4-02)
  - Claim: The energy score (logsumexp of logits) is a drop-in post-hoc replacement for softmax confidence that reduces average FPR@TPR95 by 18.03% on a CIFAR-10 WideResNet.
  - Source: https://arxiv.org/abs/2010.03759
  - For our project: Compute energy alongside MSP from the same logits (one line of code) for the OOD test on non-leaf / other-crop photos.

Related: [[energy score]], [[max softmax probability]]
