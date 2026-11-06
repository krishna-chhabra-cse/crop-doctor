# AURC

- **The model can be told to answer only when confident and pass the rest to a human, so the answers it does give are much more accurate.** (w2-03)
  - Claim: Selective classification lets a trained network abstain on low-confidence inputs to guarantee a user-chosen error rate, trading coverage for risk, which is evaluated with risk-coverage curves.
  - Source: https://arxiv.org/abs/1705.08500
  - For our project: Core evaluation for the 'I'm not sure' feature: plot field-set risk vs coverage, report AURC and the coverage achievable at a target error (e.g. 5%), with abstained images routed to the expert.

Related: [[Geifman & El-Yaniv 2017]], [[reject option]], [[risk-coverage curve]], [[selective classification]]
