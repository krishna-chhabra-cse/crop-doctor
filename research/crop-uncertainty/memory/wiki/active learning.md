# active learning

- **When you can only afford a few expert labels, asking about the photos the model is most confused by works no better than picking photos at random; picking typical, representative photos works better.** (w5-01)
  - Claim: In the low-budget regime, uncertainty-based active learning performs no better than (or worse than) random selection, and representative 'typical' examples should be queried instead (TypiClust).
  - Source: https://arxiv.org/abs/2202.02794
  - For our project: For the first rounds of expert labeling (tens of field photos), use random or clustering/typicality-based selection rather than lowest-confidence selection; switch to uncertainty only once the budget grows.
- **In a farm-image task, picking uncertain images for labeling saved more than half the labeling work compared with random picking, but only at budgets of hundreds of images.** (w5-05)
  - Claim: In an agricultural (broccoli disease/defect) instance-segmentation task, uncertainty-based active learning (MaskAL) reached the same performance with 900 images that random sampling needed 2300 images for.
  - Source: https://arxiv.org/abs/2112.06586
  - For our project: Supports that uncertainty sampling pays off at medium/high budgets (hundreds of labels) in agriculture, consistent with w5-01; our 2-week budget is likely smaller, so report it as context, not an expected gain.

Related: [[agriculture]], [[annotation cost]], [[cold start]], [[low budget]], [[TypiClust]], [[uncertainty sampling]]
