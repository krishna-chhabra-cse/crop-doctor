# calibration

- **Lab-trained models seem to learn the plain lab background instead of the disease, and few studies check whether the model knows when it is wrong.** (w1-07)
  - Claim: Recent lab-to-field papers attribute the drop to shortcut learning on PlantVillage's uniform backgrounds but rarely measure calibration. AgriPath reports no ECE and only anecdotal evidence of confident wrong predictions.
  - Source: https://arxiv.org/abs/2609.20290 ; https://arxiv.org/html/2603.13354
  - For our project: Measuring calibration (ECE, risk-coverage curves) on PlantDoc for a PlantVillage-trained model fills a real gap and is feasible in two weeks. Consider leaf cropping or background augmentation as a cheap shift mitigation.
- **A network that says it is 95% sure is often right much less than 95% of the time, but dividing its scores by one tuned number largely fixes this on familiar data.** (w2-01)
  - Claim: Modern deep CNNs are poorly calibrated (overconfident), and single-parameter temperature scaling fitted on a held-out validation set is a simple, effective post-hoc fix on in-distribution data.
  - Source: https://arxiv.org/abs/1706.04599
  - For our project: Report ECE and reliability diagrams before/after temperature scaling as our baseline calibration step, fitting T on a lab (PlantVillage-style) validation split.
- **When the new photos look different from the training photos, the model's 'I'm unsure' signal is unreliable, so using it alone to pick photos for experts can be worse than picking at random.** (w5-02)
  - Claim: Under domain shift, entropy-based uncertainty sampling frequently underperforms random sampling because target-domain uncertainty is miscalibrated, while CLUE (uncertainty-weighted clustering) gives modest consistent gains.
  - Source: https://arxiv.org/abs/2010.08666
  - For our project: Include random sampling as a mandatory baseline and try a CLUE-style (uncertain AND diverse) selector for choosing which field photos the expert labels.

Related: [[active domain adaptation]], [[AgriPath]], [[CLUE]], [[domain shift]], [[ECE]], [[Guo et al. 2017]], [[PlantDoc]], [[PlantVillage]], [[shortcut learning]], [[temperature scaling]], [[TinyCNN]], [[uncertainty sampling]]
