# TypiClust

- **When you can only afford a few expert labels, asking about the photos the model is most confused by works no better than picking photos at random; picking typical, representative photos works better.** (w5-01)
  - Claim: In the low-budget regime, uncertainty-based active learning performs no better than (or worse than) random selection, and representative 'typical' examples should be queried instead (TypiClust).
  - Source: https://arxiv.org/abs/2202.02794
  - For our project: For the first rounds of expert labeling (tens of field photos), use random or clustering/typicality-based selection rather than lowest-confidence selection; switch to uncertainty only once the budget grows.

Related: [[active learning]], [[cold start]], [[low budget]], [[uncertainty sampling]]
