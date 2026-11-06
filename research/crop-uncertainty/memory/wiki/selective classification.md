# selective classification

- **The model can be told to answer only when confident and pass the rest to a human, so the answers it does give are much more accurate.** (w2-03)
  - Claim: Selective classification lets a trained network abstain on low-confidence inputs to guarantee a user-chosen error rate, trading coverage for risk, which is evaluated with risk-coverage curves.
  - Source: https://arxiv.org/abs/1705.08500
  - For our project: Core evaluation for the 'I'm not sure' feature: plot field-set risk vs coverage, report AURC and the coverage achievable at a target error (e.g. 5%), with abstained images routed to the expert.
- **Nobody we found has measured how often a crop-disease app can safely say 'not sure' on real field photos, so that is open ground.** (w2-06)
  - Claim: The grape-leaf field study measured calibration only and did not evaluate abstention, rejection thresholds, or risk-coverage, and searches found no plant-disease paper reporting risk-coverage or conformal coverage on field photos (conformal work in plants targets species ID, e.g. Pl@ntNet).
  - Source: https://arxiv.org/abs/2507.06867
  - For our project: Our contribution: risk-coverage/AURC under lab-to-field shift for crop disease, plus how many expert-labelled field images restore a target coverage at fixed error.
- **The best alarm for 'this is not a leaf at all' is not the same as the best alarm for 'I probably got this disease wrong'.** (w4-04)
  - Claim: Misclassification detection and OOD detection need different scores: OOD detectors evaluated for selective classification with OOD data rank differently and generally fail to beat the softmax baseline.
  - Source: https://arxiv.org/abs/2207.07506
  - For our project: Report two separate evaluations: AURC/accuracy-vs-coverage on field photos (use MSP) and AUROC/FPR95 for unknown photos (use energy/KNN); possibly combine both scores.

Related: [[AURC]], [[conformal prediction]], [[energy score]], [[Geifman & El-Yaniv 2017]], [[misclassification detection]], [[Pl@ntNet]], [[plant disease]], [[reject option]], [[risk-coverage curve]], [[SIRC]]
