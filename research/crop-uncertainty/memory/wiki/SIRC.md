# SIRC

- **The best alarm for 'this is not a leaf at all' is not the same as the best alarm for 'I probably got this disease wrong'.** (w4-04)
  - Claim: Misclassification detection and OOD detection need different scores: OOD detectors evaluated for selective classification with OOD data rank differently and generally fail to beat the softmax baseline.
  - Source: https://arxiv.org/abs/2207.07506
  - For our project: Report two separate evaluations: AURC/accuracy-vs-coverage on field photos (use MSP) and AUROC/FPR95 for unknown photos (use energy/KNN); possibly combine both scores.

Related: [[energy score]], [[misclassification detection]], [[selective classification]]
