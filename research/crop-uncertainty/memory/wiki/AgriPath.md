# AgriPath

- **Lab-trained models seem to learn the plain lab background instead of the disease, and few studies check whether the model knows when it is wrong.** (w1-07)
  - Claim: Recent lab-to-field papers attribute the drop to shortcut learning on PlantVillage's uniform backgrounds but rarely measure calibration. AgriPath reports no ECE and only anecdotal evidence of confident wrong predictions.
  - Source: https://arxiv.org/abs/2609.20290 ; https://arxiv.org/html/2603.13354
  - For our project: Measuring calibration (ECE, risk-coverage curves) on PlantDoc for a PlantVillage-trained model fills a real gap and is feasible in two weeks. Consider leaf cropping or background augmentation as a cheap shift mitigation.

Related: [[calibration]], [[PlantDoc]], [[PlantVillage]], [[shortcut learning]], [[TinyCNN]]
